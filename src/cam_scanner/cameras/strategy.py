"""Evidence-aware, bounded collection on the canonical SINGLE path."""
from __future__ import annotations

import logging
import time

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
    is_valid_evidence_value,
)


class VendorFirstCollector(CameraCollector):
    """Keep one registered vendor path and one generic ONVIF path evidence-aware."""

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

    def collect_report(self, target: CameraTarget) -> CollectionReport:
        self._cached_evidence = PreAuthEvidence()
        report = self._discover(target)
        evidence = self._discovery_evidence(target)
        resolution = self._resolver.resolve_with_evidence(
            None, evidence, sensitive_values=(target.username, target.password)
        )
        if report.status is CollectionStatus.CANCELLED:
            return self._finalize(report)

        if resolution.conflicts:
            self._logger.warning(
                "Conflicting strong manufacturer evidence; native adapter selection skipped"
            )

        adapter = (
            self._registry.get(resolution.selected)
            if resolution.selected is not None and not resolution.conflicts
            else None
        )
        if adapter is not None:
            vendor_report = self._collect_source(adapter, target, source="VENDOR")
            report = report.merged(vendor_report)
            if report.status is CollectionStatus.SUCCESS or self._stopped_after_auth_failure(
                report
            ):
                return self._finalize(report)

        if report.status is CollectionStatus.CANCELLED or self._stopped_after_auth_failure(report):
            return self._finalize(report)

        generic_report = self._collect_source(self._onvif, target, source="ONVIF")
        report = report.merged(generic_report)
        if report.conflicts:
            self._logger.warning("Conflicting collection evidence retained in report")
        return self._finalize(report)

    @staticmethod
    def _finalize(report: CollectionReport) -> CollectionReport:
        return report.with_attempt(
            CollectionAttempt(
                stage="MERGE",
                operation="aggregate_collection_report",
                outcome="SUCCESS",
            )
        )

    def _discover(self, target: CameraTarget) -> CollectionReport:
        method = getattr(self._discoverer, "discover_with_report", None)
        if callable(method):
            try:
                result = method(target)
            except KeyboardInterrupt:
                return CollectionReport().with_attempt(
                    CollectionAttempt(
                        stage="DISCOVERY",
                        operation="ONVIF pre-authentication discovery",
                        protocol="ONVIF",
                        outcome="CANCELLED",
                    )
                )
            except Exception as exception:  # noqa: BLE001 - sanitized typed failure.
                return self._exception_report(
                    exception, "DISCOVERY", "ONVIF pre-authentication discovery"
                )
            if (
                isinstance(result, tuple)
                and len(result) == 2
                and isinstance(result[0], PreAuthEvidence)
                and isinstance(result[1], CollectionReport)
            ):
                self._cached_evidence = self._validated_discovery_evidence(result[0], target)
                return result[1]

        try:
            evidence = self._discoverer.discover(target)
        except KeyboardInterrupt:
            self._cached_evidence = PreAuthEvidence()
            return CollectionReport().with_attempt(
                CollectionAttempt(
                    stage="DISCOVERY",
                    operation="ONVIF pre-authentication discovery",
                    protocol="ONVIF",
                    outcome="CANCELLED",
                )
            )
        except Exception as exception:  # noqa: BLE001 - don't erase earlier report evidence.
            self._cached_evidence = PreAuthEvidence()
            return self._exception_report(
                exception, "DISCOVERY", "ONVIF pre-authentication discovery"
            )

        self._cached_evidence = self._validated_discovery_evidence(evidence, target)
        report = CollectionReport()
        if self._cached_evidence.has_evidence:
            report = report.with_evidence(
                EvidenceRecord(
                    field="onvif_reachable",
                    value="REACHABLE",
                    source="ONVIF_PREAUTH",
                    confidence="STRONG",
                    protocol="ONVIF",
                    operation="discover",
                )
            )
        resolution = self._resolver.resolve_with_evidence(
            None,
            self._cached_evidence,
            sensitive_values=(target.username, target.password),
        )
        for value in resolution.observed_values:
            if is_valid_evidence_value(
                "manufacturer", value, sensitive_values=(target.username, target.password)
            ):
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
            if is_valid_evidence_value(
                "manufacturer_signal", value, sensitive_values=(target.username, target.password)
            ):
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
        return report

    def _discovery_evidence(self, target: CameraTarget) -> PreAuthEvidence:
        # discover_with_report results are cached by the discovery step to avoid a second request.
        del target
        evidence = getattr(self, "_cached_evidence", None)
        return evidence if isinstance(evidence, PreAuthEvidence) else PreAuthEvidence()

    def _validated_discovery_evidence(
        self, evidence: PreAuthEvidence, target: CameraTarget
    ) -> PreAuthEvidence:
        """Drop raw discovery payloads after extracting safe structured signals."""
        if not isinstance(evidence, PreAuthEvidence):
            return PreAuthEvidence()
        resolution = self._resolver.resolve_with_evidence(
            None,
            evidence,
            sensitive_values=(target.username, target.password),
        )
        safe_capabilities: dict[str, tuple[str, ...]] = {}
        if resolution.observed_values:
            safe_capabilities["Manufacturer"] = resolution.observed_values
        if resolution.weak_values:
            safe_capabilities["Server"] = resolution.weak_values
        return PreAuthEvidence(capabilities=safe_capabilities)

    def _collect_source(
        self, collector: CameraCollector, target: CameraTarget, *, source: str
    ) -> CollectionReport:
        report_method = getattr(collector, "collect_report", None)
        if callable(report_method):
            try:
                report = report_method(target)
            except KeyboardInterrupt:
                return CollectionReport().with_attempt(
                    CollectionAttempt(
                        stage="SOAP",
                        operation="collect",
                        protocol="ONVIF" if source == "ONVIF" else None,
                        outcome="CANCELLED",
                    )
                )
            except Exception as exception:  # noqa: BLE001 - report unexpected failure safely.
                return self._exception_report(exception, "SOAP", "collect", source=source)
            if isinstance(report, CollectionReport):
                return report.validated_for_target((target.username, target.password))
            return CollectionReport().with_attempt(
                CollectionAttempt(
                    stage="PARSE",
                    operation="collect_report",
                    protocol="ONVIF" if source == "ONVIF" else None,
                    outcome="FAILED",
                    error_category="INVALID_RESPONSE",
                )
            )

        started = time.monotonic()
        try:
            result = collector.collect(target)
        except KeyboardInterrupt:
            return CollectionReport().with_attempt(
                CollectionAttempt(
                    stage="SOAP",
                    operation="collect",
                    protocol="ONVIF" if source == "ONVIF" else None,
                    outcome="CANCELLED",
                    duration=self._elapsed(started),
                )
            )
        except Exception as exception:  # noqa: BLE001
            return self._exception_report(
                exception, "SOAP", "collect", source=source, started=started
            )

        if not isinstance(result, CameraResult):
            return CollectionReport().with_attempt(
                CollectionAttempt(
                    stage="PARSE",
                    operation="collect_result",
                    protocol="ONVIF" if source == "ONVIF" else None,
                    outcome="FAILED",
                    duration=self._elapsed(started),
                    error_category="INVALID_RESPONSE",
                )
            )
        report = CollectionReport.from_camera_result(
            result,
            source=source,
            sensitive_values=(target.username, target.password),
        )
        return report.merged(
            CollectionReport(
                attempts=(
                    CollectionAttempt(
                        stage="SOAP",
                        operation="collect",
                        protocol="ONVIF" if source == "ONVIF" else None,
                        outcome=(
                            "CANCELLED"
                            if result.status is CollectionStatus.CANCELLED
                            else "FAILED"
                            if result.status is CollectionStatus.FAILED
                            else "SUCCESS"
                        ),
                        duration=self._elapsed(started),
                    ),
                ),
                cancelled=result.status is CollectionStatus.CANCELLED,
            )
        )

    def _exception_report(
        self,
        exception: BaseException,
        stage: str,
        operation: str,
        *,
        source: str = "ONVIF",
        started: float | None = None,
    ) -> CollectionReport:
        category, http_status, protocol_code = normalize_collection_error(exception, stage=stage)
        attempt_stage = self._stage_for(category, stage)
        return CollectionReport().with_attempt(
            CollectionAttempt(
                stage=attempt_stage,
                operation=operation,
                protocol="ONVIF" if source == "ONVIF" else None,
                outcome="FAILED",
                duration=self._elapsed(started) if started is not None else 0.0,
                http_status=http_status,
                protocol_code=protocol_code,
                error_category=category,
            )
        )

    @staticmethod
    def _elapsed(started: float) -> float:
        return max(0.0, float(time.monotonic() - started))

    @staticmethod
    def _stage_for(category: str, default: str) -> str:
        if category in {"CONNECT_TIMEOUT", "CONNECTION_REFUSED", "TLS_ERROR"}:
            return "CONNECT"
        if category in {"AUTH_REJECTED", "AUTHORIZATION_DENIED", "AUTH_MECHANISM_UNSUPPORTED"}:
            return "AUTH"
        if category in {"READ_TIMEOUT", "HTTP_ERROR", "ENDPOINT_UNSUPPORTED"}:
            return "HTTP"
        if category == "SOAP_FAULT":
            return "SOAP"
        if category == "INVALID_RESPONSE":
            return "PARSE"
        return default

    @staticmethod
    def _stopped_after_auth_failure(report: CollectionReport) -> bool:
        return any(
            item.error_category in {"AUTH_REJECTED", "AUTHORIZATION_DENIED"}
            for item in report.attempts
        )
