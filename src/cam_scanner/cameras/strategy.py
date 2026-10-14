"""Vendor-first collection routing over the canonical domain evidence contracts."""
from __future__ import annotations

import logging
from builtins import TimeoutError

from cam_scanner.cameras.collector import CameraCollector
from cam_scanner.cameras.manufacturer import ManufacturerNormalizer
from cam_scanner.cameras.onvif.adapter import GenericOnvifCollector
from cam_scanner.cameras.preauth import (
    ManufacturerResolver,
    OnvifPreAuthDiscoverer,
    PreAuthEvidence,
)
from cam_scanner.cameras.registry import AdapterRegistry
from cam_scanner.domain.enums import CollectionStatus
from cam_scanner.domain.models import (
    CameraResult,
    CameraTarget,
    CollectionAttempt,
    CollectionReport,
    EvidenceRecord,
)


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
        self._normalizer = ManufacturerNormalizer()
        self._logger = logger or logging.getLogger("cam_scanner")

    def collect(self, target: CameraTarget) -> CameraResult:
        return self.collect_report(target).to_camera_result(target.ip)

    def collect_report(self, target: CameraTarget) -> CollectionReport:
        report = CollectionReport()
        report = CollectionReport()
        try:
            discover_with_report = getattr(self._discoverer, "discover_with_report", None)
            if callable(discover_with_report):
                preauth, preauth_report = discover_with_report(target)
                if isinstance(preauth_report, CollectionReport):
                    report = report.merged(preauth_report).validated_for_target(
                        (target.username, target.password)
                    )
            else:
                preauth = self._discoverer.discover(target)
        except KeyboardInterrupt:
            return report.with_attempt(
                CollectionAttempt(
                    stage="DISCOVERY",
                    operation="discover",
                    protocol="ONVIF",
                    outcome="CANCELLED",
                )
            )
        except Exception:  # noqa: BLE001 - discovery failure permits generic ONVIF collection.
            preauth = PreAuthEvidence()
        if preauth is None:
            preauth = PreAuthEvidence()

        resolution = self._resolver.resolve_with_evidence(
            None,
            preauth,
            sensitive_values=(target.username, target.password),
        )
        manufacturer = resolution.selected
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
        adapter = self._registry.get(manufacturer) if manufacturer else None
        if adapter is not None:
            try:
                collect_report = getattr(adapter, "collect_report", None)
                if callable(collect_report):
                    vendor_report = collect_report(target)
                    if isinstance(vendor_report, CollectionReport):
                        report = report.merged(vendor_report).validated_for_target(
                            (target.username, target.password)
                        )
                    else:
                        result = adapter.collect(target)
                        if isinstance(result, CameraResult):
                            report = report.merged(
                                CollectionReport.from_camera_result(
                                    result,
                                    source="VENDOR",
                                    sensitive_values=(target.username, target.password),
                                )
                            )
                else:
                    result = adapter.collect(target)
                    if isinstance(result, CameraResult):
                        report = report.merged(
                            CollectionReport.from_camera_result(
                                result,
                                source="VENDOR",
                                sensitive_values=(target.username, target.password),
                            )
                        )
            except Exception:  # noqa: BLE001 - raw vendor exceptions are never retained.
                self._logger.warning("Registered vendor adapter failed; using controlled ONVIF fallback")
            else:
                if _authentication_rejected(report):
                    return report
                if report.to_camera_result(target.ip).status is CollectionStatus.SUCCESS:
                    return report

        try:
            collect_report = getattr(self._onvif, "collect_report", None)
            if callable(collect_report):
                onvif_report = collect_report(target)
                if isinstance(onvif_report, CollectionReport):
                    combined = report.merged(onvif_report).validated_for_target(
                        (target.username, target.password)
                    )
                    _log_conflicts(self._logger, combined)
                    return combined
                raise TypeError("ONVIF collector returned an unsupported report")
            result = self._onvif.collect(target)
        except KeyboardInterrupt:
            return report.with_attempt(
                CollectionAttempt(
                    stage="SOAP",
                    operation="GetDeviceInformation",
                    protocol="ONVIF",
                    outcome="CANCELLED",
                )
            )
        except Exception as exception:  # noqa: BLE001 - retain only a bounded failure category.
            category = _failure_category(exception)
            return report.with_attempt(
                CollectionAttempt(
                    stage="AUTH" if category in {"AUTH_REJECTED", "AUTHORIZATION_DENIED"} else "SOAP",
                    operation="GetDeviceInformation",
                    protocol="ONVIF",
                    outcome="FAILED",
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
        _log_conflicts(self._logger, combined)
        return combined


def _authentication_rejected(report: CollectionReport) -> bool:
    return any(
        attempt.error_category in {"AUTH_REJECTED", "AUTHORIZATION_DENIED"}
        for attempt in report.attempts
    )


def _failure_category(exception: Exception) -> str:
    chain: list[BaseException] = []
    current: BaseException | None = exception
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        chain.append(current)
        original = getattr(current, "original_exception", None)
        current = original if isinstance(original, BaseException) else current.__cause__ or current.__context__
    if any(getattr(getattr(item, "response", None), "status_code", None) == 403 for item in chain):
        return "AUTHORIZATION_DENIED"
    if any(
        getattr(getattr(item, "response", None), "status_code", None) == 401
        or any(
            marker in str(item).casefold().replace("_", "")
            for marker in ("notauthorized", "unauthorized", "authentication failed", "invalid credentials")
        )
        for item in chain
    ):
        return "AUTH_REJECTED"
    if any(isinstance(item, TimeoutError) or type(item).__name__ in {"ConnectTimeout", "ReadTimeout", "Timeout"} for item in chain):
        return "READ_TIMEOUT"
    if any(
        type(item).__name__ in {"ConnectionError", "ConnectError"} or isinstance(item, OSError)
        for item in chain
    ):
        return "CONNECTION_REFUSED"
    if any(type(item).__module__.startswith(("zeep", "onvif")) for item in chain):
        return "SOAP_FAULT"
    return "UNEXPECTED"










def _log_conflicts(logger: logging.Logger, report: CollectionReport) -> None:
    if report.conflicts:
        logger.warning("Conflicting collection evidence retained in report")
