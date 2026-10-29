"""Vendor-first collection routing over the canonical domain evidence contracts."""
from __future__ import annotations

import inspect
import logging
from dataclasses import replace

from cam_scanner.application.collection_context import CollectionDeadlineExceeded
from cam_scanner.cameras.collector import CameraCollector
from cam_scanner.cameras.onvif.adapter import GenericOnvifCollector
from cam_scanner.cameras.preauth import (
    ManufacturerResolver,
    OnvifPreAuthDiscoverer,
    PreAuthEvidence,
)
from cam_scanner.cameras.registry import AdapterRegistry
from cam_scanner.domain.enums import CollectionStatus
from cam_scanner.domain.errors import normalize_collection_error
from cam_scanner.domain.models import (
    CameraResult,
    CameraTarget,
    CollectionAttempt,
    CollectionReport,
    EvidenceRecord,
)

_PANASONIC_PROFILE = "i-pro-command-interface-v1.17:WV-S2531L"


class VendorFirstCollector(CameraCollector):
    """Select at most one identified vendor adapter, then use ONVIF as a controlled fallback."""

    def __init__(
        self,
        onvif_collector: CameraCollector | None = None,
        registry: AdapterRegistry | None = None,
        discoverer: OnvifPreAuthDiscoverer | None = None,
        resolver: ManufacturerResolver | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._onvif = onvif_collector or GenericOnvifCollector()
        self._registry = registry or AdapterRegistry()
        self._discoverer = discoverer or OnvifPreAuthDiscoverer()
        self._resolver = resolver or ManufacturerResolver()
        self._logger = logger or logging.getLogger("cam_scanner")

    def collect(self, target: CameraTarget) -> CameraResult:
        return self.collect_report(target).to_camera_result(target.ip)

    def collect_report(self, target: CameraTarget, *, context: object | None = None) -> CollectionReport:
        report = CollectionReport()
        declared_hint = getattr(context, "manufacturer_hint", None)
        # A declared hint can skip anonymous discovery only for native collectors
        # already known to return all IDENTITY_V1 fields. Registry membership alone
        # is insufficient (notably Bosch and Panasonic in this release).
        hinted_resolution = self._resolver.resolve_with_evidence(
            declared_hint,
            PreAuthEvidence(),
            sensitive_values=(target.username, target.password),
        )
        hinted_adapter = (
            self._registry.get(hinted_resolution.selected)
            if hinted_resolution.selected
            else None
        )
        if hinted_adapter is not None and not _hint_adapter_covers_identity(
            hinted_resolution.selected, hinted_adapter, context=context
        ):
            hinted_adapter = None
        panasonic_model_hint = getattr(context, "model_hint", None)
        if (hinted_resolution.selected == "Panasonic"
                and (panasonic_model_hint is None
                     or getattr(panasonic_model_hint, "match_key", "") != "wv-s2531l")):
            # A declared Panasonic family without the exact documented profile
            # cannot route to native CGI or trigger discovery as a fallback.
            return _attach_resolution(
                _skip_panasonic_source(report.with_attempt(CollectionAttempt(
                    stage="DISCOVERY",
                    operation="preauth_discovery",
                    protocol="ONVIF",
                    outcome="SKIPPED",
                ))),
                declared_hint,
                self._resolver,
                target,
            )
        preauth = PreAuthEvidence()
        if hinted_adapter is None:
            try:
                discover_with_report = getattr(self._discoverer, "discover_with_report", None)
                if callable(discover_with_report):
                    preauth, preauth_report = _call_with_context(discover_with_report, target, context)
                    if isinstance(preauth_report, CollectionReport):
                        report = report.merged(preauth_report).validated_for_target(
                            (target.username, target.password)
                        )
                else:
                    discover = self._discoverer.discover
                    preauth = _call_with_context(discover, target, context)
            except KeyboardInterrupt:
                _request_cancel(context)
                return report.with_attempt(
                    CollectionAttempt(
                        stage="DISCOVERY",
                        operation="discover",
                        protocol="ONVIF",
                        outcome="CANCELLED",
                    )
                )
            except Exception as exception:  # noqa: BLE001 - preserve TLS failures as terminal.
                category, _, _ = normalize_collection_error(exception, stage="CONNECT")
                if category == "TLS_ERROR":
                    _mark_tls_failure(context)
                    report = report.with_attempt(CollectionAttempt(
                        stage="CONNECT", operation="preauth_discovery", protocol="ONVIF",
                        outcome="FAILED", error_category=category,
                    ))
                    return _attach_resolution(report, declared_hint, self._resolver, target)
                preauth = PreAuthEvidence()
            if _has_tls_failure(report):
                _mark_tls_failure(context)
                return _attach_resolution(report, declared_hint, self._resolver, target)
            if report.status is CollectionStatus.CANCELLED or _is_cancelled(context):
                return _cancelled_report(report, stage="DISCOVERY", operation="discover")
            if preauth is None:
                preauth = PreAuthEvidence()

        # Resolution is attached after observed vendor evidence is available, so
        # declared-only routing cannot overwrite or conflict with the observation.
        resolution = self._resolver.resolve_with_evidence(
            declared_hint,
            preauth,
            sensitive_values=(target.username, target.password),
        )
        manufacturer = (
            hinted_resolution.selected if hinted_adapter is not None else resolution.selected
        )
        for value in resolution.observed_values:
            report = report.with_evidence(
                EvidenceRecord(
                    field="manufacturer",
                    value=value,
                    source="ONVIF_PREAUTH",
                    confidence="STRONG",
                    protocol="ONVIF",
                    operation="GetCapabilities",
                )
            )
        for value in resolution.weak_values:
            report = report.with_evidence(
                EvidenceRecord(
                    field="manufacturer_signal",
                    value=value,
                    source="ONVIF_PREAUTH",
                    confidence="WEAK",
                    protocol="ONVIF",
                    operation="GetCapabilities",
                )
            )
        report = report.validated_for_target((target.username, target.password))
        adapter = hinted_adapter or (self._registry.get(manufacturer) if manufacturer else None)
        if adapter is not None and not _hint_adapter_covers_identity(
            manufacturer, adapter, context=context
        ):
            adapter = None
        if adapter is None and (
            manufacturer == "Panasonic" or "Panasonic" in resolution.conflicts
        ):
            report = _skip_panasonic_source(report)
        if adapter is not None:
            vendor_attempt_start = len(report.attempts)
            try:
                if context is not None:
                    context.check("NATIVE")
                    if manufacturer == "Panasonic":
                        context.panasonic_profile = _PANASONIC_PROFILE
                    vendor_family = _vendor_auth_family(manufacturer)
                    # Bosch currently has no native authenticated request.
                    real_axis_public = False
                    if manufacturer == "Axis":
                        from cam_scanner.cameras.manufacturers.axis import AxisAdapter

                        real_axis_public = (
                            type(adapter) is AxisAdapter
                            and inspect.ismethod(getattr(adapter, "collect_report", None))
                        )
                    if vendor_family is not None and not real_axis_public and not context.auth.begin(
                        vendor_family, "initial"
                    ):
                        return _attach_resolution(report, declared_hint, self._resolver, target)
                collect_report = getattr(adapter, "collect_report", None)
                if callable(collect_report):
                    vendor_report = _call_with_context(collect_report, target, context)
                    if isinstance(vendor_report, CollectionReport):
                        report = report.merged(vendor_report).validated_for_target(
                            (target.username, target.password)
                        )
                    else:
                        result = _call_with_context(adapter.collect, target, context)
                        if isinstance(result, CameraResult):
                            report = report.merged(
                                CollectionReport.from_camera_result(
                                    result,
                                    source="VENDOR",
                                    sensitive_values=(target.username, target.password),
                                )
                            )
                else:
                    result = _call_with_context(adapter.collect, target, context)
                    if isinstance(result, CameraResult):
                        report = report.merged(
                            CollectionReport.from_camera_result(
                                result,
                                source="VENDOR",
                                sensitive_values=(target.username, target.password),
                            )
                        )
            except KeyboardInterrupt:
                _request_cancel(context)
                return _cancelled_report(
                    report, stage="CONNECT", operation="vendor_adapter"
                )
            except Exception as exception:  # noqa: BLE001 - raw errors are never retained.
                if _is_cancelled(context):
                    return _cancelled_report(
                        report, stage="CONNECT", operation="vendor_adapter"
                    )
                if manufacturer == "Axis" and isinstance(exception, CollectionDeadlineExceeded):
                    report = report.with_attempt(CollectionAttempt(
                        stage="CONNECT", operation="vendor_adapter", outcome="FAILED",
                        error_category="DEADLINE_EXCEEDED",
                    ))
                    return _attach_resolution(report, declared_hint, self._resolver, target)
                category, _, _ = normalize_collection_error(
                    exception, stage="CONNECT", authenticated=True
                )
                if category == "TLS_ERROR":
                    _mark_tls_failure(context)
                    report = report.with_attempt(CollectionAttempt(
                        stage="CONNECT", operation="vendor_adapter", outcome="FAILED",
                        error_category=category,
                    ))
                    return _attach_resolution(report, declared_hint, self._resolver, target)
                report = report.with_attempt(CollectionAttempt(
                    stage="CONNECT", operation="vendor_adapter", outcome="FAILED",
                    error_category=category,
                ))
                if category in {"AUTH_REJECTED", "AUTHORIZATION_DENIED"}:
                    return _attach_resolution(report, declared_hint, self._resolver, target)
                self._logger.warning("Registered vendor adapter failed; using controlled ONVIF fallback")
            else:
                if _has_tls_failure(report):
                    _mark_tls_failure(context)
                    return _attach_resolution(report, declared_hint, self._resolver, target)
                if _is_cancelled(context):
                    return _cancelled_report(
                        report, stage="CONNECT", operation="vendor_adapter"
                    )
                if manufacturer == "Axis" and any(
                    attempt.error_category in {"DEADLINE_EXCEEDED", "INVALID_RESPONSE"}
                    for attempt in report.attempts[vendor_attempt_start:]
                ):
                    return _attach_resolution(report, declared_hint, self._resolver, target)
                if _authentication_rejected(report) or _authentication_blocked(context):
                    return _attach_resolution(report, declared_hint, self._resolver, target)
                if report.to_camera_result(target.ip).status is CollectionStatus.SUCCESS:
                    return _attach_resolution(report, declared_hint, self._resolver, target)

        report = _attach_resolution(report, declared_hint, self._resolver, target)

        try:
            if context is not None:
                if context.cancelled:
                    return _cancelled_report(
                        report, stage="SOAP", operation="collect_report"
                    )
                if _authentication_blocked(context):
                    return report
                context.check("ONVIF")
                missing_fields = _missing_identity_fields(report, target.ip)
                reason = "missing_identity" if context.auth.logical_attempts else "initial"
                if not context.auth.begin(
                    "ONVIF", reason, missing_identity_fields=missing_fields
                ):
                    return report
            collect_report = getattr(self._onvif, "collect_report", None)
            if callable(collect_report):
                onvif_report = _call_with_context(collect_report, target, context)
                if isinstance(onvif_report, CollectionReport):
                    combined = report.merged(onvif_report).validated_for_target(
                        (target.username, target.password)
                    )
                    combined = _attach_resolution(
                        combined, declared_hint, self._resolver, target
                    )
                    _log_conflicts(self._logger, combined)
                    return combined
                raise TypeError("ONVIF collector returned an unsupported report")
            result = _call_with_context(self._onvif.collect, target, context)
        except KeyboardInterrupt:
            _request_cancel(context)
            return _cancelled_report(
                report, stage="SOAP", operation="GetDeviceInformation"
            )
        except Exception as exception:  # noqa: BLE001 - retain only a bounded failure category.
            if _is_cancelled(context):
                return _cancelled_report(
                    report, stage="SOAP", operation="collect_report"
                )
            category, http_status, protocol_code = normalize_collection_error(
                exception, stage="SOAP", authenticated=True
            )
            if category == "TLS_ERROR":
                _mark_tls_failure(context)
            return report.with_attempt(
                CollectionAttempt(
                    stage="AUTH" if category in {"AUTH_REJECTED", "AUTHORIZATION_DENIED"} else "SOAP",
                    operation="GetDeviceInformation",
                    protocol="ONVIF",
                    outcome="FAILED",
                    http_status=http_status,
                    protocol_code=protocol_code,
                    error_category=category,
                    authentication_mechanism="WS_SECURITY_USERNAME_TOKEN",
                )
            ).validated_for_target((target.username, target.password))

        if not isinstance(result, CameraResult):
            return report.with_attempt(
                CollectionAttempt(
                    stage="SOAP",
                    operation="GetDeviceInformation",
                    protocol="ONVIF",
                    outcome="FAILED",
                    error_category="UNEXPECTED",
                )
            )
        onvif_report = CollectionReport.from_camera_result(
            result,
            source="ONVIF_AUTHENTICATED",
            sensitive_values=(target.username, target.password),
        )
        if result.status in {CollectionStatus.SUCCESS, CollectionStatus.PARTIAL_SUCCESS}:
            onvif_report = onvif_report.with_attempt(
                CollectionAttempt(
                    stage="SOAP",
                    operation="GetDeviceInformation",
                    protocol="ONVIF",
                    outcome="SUCCESS",
                    duration=result.duration,
                    authentication_mechanism="WS_SECURITY_USERNAME_TOKEN",
                )
            )
        combined = report.merged(onvif_report).validated_for_target(
            (target.username, target.password)
        )
        combined = _attach_resolution(combined, declared_hint, self._resolver, target)
        if _has_tls_failure(combined):
            _mark_tls_failure(context)
        _log_conflicts(self._logger, combined)
        return combined


def _authentication_rejected(report: CollectionReport) -> bool:
    return any(
        attempt.error_category in {"AUTH_REJECTED", "AUTHORIZATION_DENIED"}
        or (
            attempt.error_category == "SOAP_FAULT"
            and _is_not_authorized(attempt.protocol_code)
            and attempt.authentication_mechanism != "NONE"
        )
        for attempt in report.attempts
    )


def _has_tls_failure(report: CollectionReport) -> bool:
    return any(attempt.error_category == "TLS_ERROR" for attempt in report.attempts)


def _mark_tls_failure(context: object | None) -> None:
    marker = getattr(context, "mark_tls_failure", None)
    if callable(marker):
        marker()


def _request_cancel(context: object | None) -> None:
    event = getattr(context, "cancel_event", None)
    setter = getattr(event, "set", None)
    if callable(setter):
        setter()


def _is_cancelled(context: object | None) -> bool:
    return bool(getattr(context, "cancelled", False))


def _cancelled_report(
    report: CollectionReport, *, stage: str, operation: str
) -> CollectionReport:
    _request_cancelled = any(attempt.outcome == "CANCELLED" for attempt in report.attempts)
    attempts = report.attempts
    if not report.cancelled and not _request_cancelled:
        attempts += (
            CollectionAttempt(
                stage=stage,
                operation=operation,
                outcome="CANCELLED",
            ),
        )
    return replace(report, attempts=attempts, cancelled=True)


def _call_with_context(method: object, target: CameraTarget, context: object | None) -> object:
    """Keep injected legacy test collectors compatible while forwarding production context."""
    if context is not None and callable(method):
        try:
            parameters = inspect.signature(method).parameters
        except (TypeError, ValueError):
            parameters = {}
        if "context" in parameters:
            return method(target, context=context)
    return method(target)  # type: ignore[operator]


def _authentication_blocked(context: object | None) -> bool:
    if context is None:
        return False
    return context.auth.state in {
        context.auth.AUTH_REJECTED_FINAL,
        context.auth.AUTHORIZATION_DENIED,
    } or context.auth.soap_access_blocked


def _skip_panasonic_source(report: CollectionReport) -> CollectionReport:
    """Record an ineligible source without claiming a network exchange occurred."""
    return report.with_attempt(CollectionAttempt(
        stage="VALIDATE",
        operation="GET /cgi-bin/getinfo",
        outcome="SKIPPED",
        error_category="ENDPOINT_UNSUPPORTED",
    ))


def _vendor_auth_family(manufacturer: str | None) -> str | None:
    normalized = (manufacturer or "").casefold().replace("/", " ").replace("-", " ")
    if "bosch" in normalized:
        return None
    for marker, family in (
        ("axis", "VENDOR_AXIS"),
        ("hikvision", "VENDOR_HIKVISION"),
        ("dahua", "VENDOR_DAHUA"),
        ("panasonic", "VENDOR_PANASONIC"),
        ("i-pro", "VENDOR_PANASONIC"),
        ("hanwha", "VENDOR_SAMSUNG/HANWHA"),
        ("samsung", "VENDOR_SAMSUNG/HANWHA"),
    ):
        if marker in normalized:
            return family
    return None


def _hint_adapter_covers_identity(
    manufacturer: str, adapter: object, *, context: object | None = None
) -> bool:
    """Only the shipped, documented parsers can bypass anonymous discovery."""
    supported_types: dict[str, type] = {}
    if manufacturer == "Axis":
        from cam_scanner.cameras.manufacturers.axis import AxisAdapter

        supported_types[manufacturer] = AxisAdapter
    elif manufacturer == "Hikvision":
        from cam_scanner.cameras.manufacturers.hikvision import HikvisionAdapter

        supported_types[manufacturer] = HikvisionAdapter
    elif manufacturer == "Dahua":
        from cam_scanner.cameras.manufacturers.dahua import DahuaAdapter

        supported_types[manufacturer] = DahuaAdapter
    elif manufacturer == "Samsung/Hanwha":
        from cam_scanner.cameras.manufacturers.samsung_hanwha import SamsungHanwhaAdapter

        supported_types[manufacturer] = SamsungHanwhaAdapter
    elif manufacturer == "Panasonic":
        from cam_scanner.cameras.manufacturers.panasonic import PanasonicAdapter

        supported_types[manufacturer] = PanasonicAdapter
    supported_type = supported_types.get(manufacturer)
    if supported_type is None or type(adapter) is not supported_type:
        return False
    if manufacturer == "Panasonic":
        hint = getattr(context, "model_hint", None)
        return bool(hint is not None and getattr(hint, "match_key", "") == "wv-s2531l")
    return True


def _attach_resolution(
    report: CollectionReport,
    declared_hint: str | None,
    resolver: ManufacturerResolver,
    target: CameraTarget,
) -> CollectionReport:
    strong = tuple(
        dict.fromkeys(
            item.value
            for item in report.evidence
            if item.field == "manufacturer" and item.confidence == "STRONG"
        )
    )
    weak = tuple(
        dict.fromkeys(
            item.value for item in report.evidence if item.field == "manufacturer_signal"
        )
    )
    evidence = PreAuthEvidence(
        capabilities={"Manufacturer": strong, "Server": weak}
    )
    resolution = resolver.resolve_with_evidence(
        declared_hint,
        evidence,
        sensitive_values=(target.username, target.password),
    )
    # Reconcile after every merge: authenticated ONVIF may add identity evidence
    # after the initial preauth resolution was attached.
    if report.manufacturer_resolution != resolution:
        report = replace(report, manufacturer_resolution=resolution)
    return report


def _missing_identity_fields(report: CollectionReport, ip: str) -> tuple[str, ...]:
    result = report.to_camera_result(ip)
    return tuple(
        field
        for field in ("manufacturer", "model", "serial")
        if not getattr(result, field, None)
    )


def _is_not_authorized(protocol_code: str | None) -> bool:
    return isinstance(protocol_code, str) and "notauthorized" in protocol_code.replace(
        "_", ""
    ).casefold()










def _log_conflicts(logger: logging.Logger, report: CollectionReport) -> None:
    if report.conflicts:
        logger.warning("Conflicting collection evidence retained in report")
