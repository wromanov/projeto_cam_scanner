"""Offline acceptance coverage for P2-I1 evidence, manufacturer, and diagnostics."""
import logging
from dataclasses import fields
from io import StringIO

import pytest
from zeep.exceptions import Fault

from cam_scanner.application.inventory_service import InventoryService
from cam_scanner.cameras.preauth import (
    ManufacturerResolver,
    OnvifPreAuthDiscoverer,
    PreAuthEvidence,
)
from cam_scanner.cameras.strategy import VendorFirstCollector
from cam_scanner.domain.enums import CollectionMethod, CollectionStatus, ErrorCode
from cam_scanner.domain.errors import normalize_collection_error
from cam_scanner.domain.models import (
    CameraResult,
    CameraTarget,
    CollectionAttempt,
    CollectionReport,
    EvidenceRecord,
)

IP = "192.0.2.80"
SECRET = "NeverPrint-Secret-7731"


def _record(field: str, value: str, *, source: str = "FIXTURE", confidence: str = "STRONG"):
    return EvidenceRecord(
        field=field,
        value=value,
        source=source,
        confidence=confidence,
        protocol="ONVIF",
        operation="GetDeviceInformation",
    )


def _identity(*, firmware: str | None = None) -> CollectionReport:
    records = [
        _record("manufacturer", "Hikvision"),
        _record("model", "DS-2CD"),
        _record("serial", "SN-42"),
    ]
    if firmware is not None:
        records.append(_record("firmware", firmware))
    return CollectionReport(evidence=tuple(records))


class _Discoverer:
    def __init__(self, capabilities: object | None = None) -> None:
        self.evidence = PreAuthEvidence(capabilities=capabilities)

    def discover(self, _target: CameraTarget) -> PreAuthEvidence:
        return self.evidence


class _Collector:
    def __init__(
        self, result: CameraResult | None = None, error: BaseException | None = None
    ) -> None:
        self.result = result
        self.error = error
        self.calls = 0

    def collect(self, _target: CameraTarget) -> CameraResult:
        self.calls += 1
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


def test_f01_preauth_identity_survives_read_timeout() -> None:
    onvif = _Collector(error=TimeoutError("fixture timeout"))
    collector = VendorFirstCollector(
        onvif_collector=onvif,
        discoverer=_Discoverer({"Manufacturer": "Hikvision"}),
    )

    report = collector.collect_report(CameraTarget(IP, "operator", SECRET))
    result = report.to_camera_result(IP)

    assert result.status is CollectionStatus.PARTIAL_SUCCESS
    assert result.manufacturer == "Hikvision"
    assert result.model is None and result.serial is None
    assert any(item.error_category == "READ_TIMEOUT" for item in report.attempts)
    assert report.missing_fields == ("model", "serial")


def test_exception_and_failed_result_have_equivalent_aggregate_semantics() -> None:
    exception_report = VendorFirstCollector(
        onvif_collector=_Collector(error=TimeoutError("read timed out")),
        discoverer=_Discoverer({"Manufacturer": "Hikvision"}),
    ).collect_report(CameraTarget(IP, "operator", SECRET))
    failed_report = VendorFirstCollector(
        onvif_collector=_Collector(
            CameraResult(
                ip=IP,
                status=CollectionStatus.FAILED,
                error_code=ErrorCode.TIMEOUT,
                error_message="sanitized timeout",
                collection_method=CollectionMethod.ONVIF,
            )
        ),
        discoverer=_Discoverer({"Manufacturer": "Hikvision"}),
    ).collect_report(CameraTarget(IP, "operator", SECRET))

    exception_result = exception_report.to_camera_result(IP)
    failed_result = failed_report.to_camera_result(IP)
    assert exception_result.status is failed_result.status is CollectionStatus.PARTIAL_SUCCESS
    assert exception_result.manufacturer == failed_result.manufacturer == "Hikvision"
    assert exception_result.error_code is failed_result.error_code is ErrorCode.TIMEOUT
    assert any(item.error_category == "READ_TIMEOUT" for item in exception_report.attempts)
    assert any(item.error_category == "READ_TIMEOUT" for item in failed_report.attempts)


@pytest.mark.parametrize("firmware", [None, "5.1.0"])
def test_identity_v1_complete_without_or_with_firmware_is_success(firmware: str | None) -> None:
    result = _identity(firmware=firmware).to_camera_result(IP)
    assert result.status is CollectionStatus.SUCCESS
    assert result.manufacturer == "Hikvision"
    assert result.model == "DS-2CD" and result.serial == "SN-42"
    assert result.firmware == firmware


def test_identity_v1_manufacturer_only_is_partial() -> None:
    result = CollectionReport(evidence=(_record("manufacturer", "Hikvision"),)).to_camera_result(IP)
    assert result.status is CollectionStatus.PARTIAL_SUCCESS
    assert result.manufacturer == "Hikvision"
    assert result.error_message and "model, serial" in result.error_message


def test_identity_v1_manufacturer_and_model_without_serial_is_partial() -> None:
    report = CollectionReport(
        evidence=(_record("manufacturer", "Hikvision"), _record("model", "DS-2CD"))
    )
    result = report.to_camera_result(IP)
    assert result.status is CollectionStatus.PARTIAL_SUCCESS
    assert report.missing_fields == ("serial",)


def test_no_useful_evidence_is_failed() -> None:
    result = CollectionReport().with_attempt(
        CollectionAttempt(
            stage="HTTP",
            operation="GetDeviceInformation",
            protocol="ONVIF",
            outcome="FAILED",
            error_category="READ_TIMEOUT",
        )
    ).to_camera_result(IP)
    assert result.status is CollectionStatus.FAILED
    assert result.error_code is ErrorCode.TIMEOUT


@pytest.mark.parametrize(
    ("field", "value", "confidence"),
    [
        ("onvif_reachable", "GetCapabilities", "STRONG"),
        ("manufacturer_signal", "Axis", "WEAK"),
    ],
)
def test_diagnostic_or_weak_signal_alone_is_not_useful_identity(
    field: str, value: str, confidence: str
) -> None:
    report = CollectionReport(
        evidence=(
            EvidenceRecord(
                field=field,
                value=value,
                source="ONVIF_PREAUTH",
                confidence=confidence,
                protocol="ONVIF",
                operation="GetCapabilities",
            ),
        )
    )
    assert report.status is CollectionStatus.FAILED
    assert report.to_camera_result(IP).status is CollectionStatus.FAILED


def test_f01_valid_evidence_survives_a_later_exception_and_fallback_failure() -> None:
    onvif = _Collector(error=RuntimeError("fallback unavailable"))
    report = VendorFirstCollector(
        onvif_collector=onvif,
        discoverer=_Discoverer({"Manufacturer": "Hikvision"}),
    ).collect_report(CameraTarget(IP, "operator", SECRET))
    assert report.value_for("manufacturer", require_strong=True) == "Hikvision"
    assert report.status is CollectionStatus.PARTIAL_SUCCESS
    assert len(report.attempts) >= 1


def test_f01_cancellation_keeps_evidence_and_does_not_start_another_source() -> None:
    onvif = _Collector(error=KeyboardInterrupt())
    report = VendorFirstCollector(
        onvif_collector=onvif,
        discoverer=_Discoverer({"Manufacturer": "Hikvision"}),
    ).collect_report(CameraTarget(IP, "operator", SECRET))
    result = report.to_camera_result(IP)
    assert result.status is CollectionStatus.CANCELLED
    assert result.manufacturer == "Hikvision"
    assert onvif.calls == 1


def test_conflicting_identity_values_are_preserved_and_prevent_success() -> None:
    report = _identity().merged(
        CollectionReport(evidence=(_record("manufacturer", "Axis", source="SECOND_SOURCE"),))
    )
    result = report.to_camera_result(IP)
    assert report.conflicts == ("manufacturer",)
    assert len(report.conflict_records[0][1]) == 2
    assert result.status is CollectionStatus.PARTIAL_SUCCESS
    assert result.manufacturer is None
    assert "Conflito de evidência em manufacturer" in (result.error_message or "")


def test_invalid_or_empty_value_cannot_replace_a_valid_value() -> None:
    report = _identity().merged(
        CollectionReport.from_camera_result(
            CameraResult(ip=IP, status=CollectionStatus.SUCCESS, model="N/A")
        )
    )
    assert report.value_for("model") == "DS-2CD"
    assert report.status is CollectionStatus.SUCCESS


@pytest.mark.parametrize(
    ("hint", "capabilities", "selected", "resolved", "confidence", "mismatch"),
    [
        ("Axis", {"Manufacturer": "Axis Communications"}, "Axis", "Axis", "STRONG", False),
        ("Axis", {"Manufacturer": "Hikvision"}, "Hikvision", "Hikvision", "STRONG", True),
        (None, {"Server": "Axis"}, None, None, "WEAK", False),
        (None, {}, None, None, "UNKNOWN", False),
        (None, {"Manufacturer": ["Axis", "Hikvision"]}, None, None, "CONFLICTING", False),
    ],
)
def test_f02_resolution_tracks_hint_observation_confidence_and_conflict(
    hint: str | None,
    capabilities: object,
    selected: str | None,
    resolved: str | None,
    confidence: str,
    mismatch: bool,
) -> None:
    resolution = ManufacturerResolver().resolve_with_evidence(
        hint, PreAuthEvidence(capabilities=capabilities)
    )
    assert resolution.selected == selected
    assert resolution.resolved == resolved
    assert resolution.confidence == confidence
    assert resolution.mismatch is mismatch
    assert resolution.declared == hint


def test_f02_conflicting_signal_order_does_not_change_resolution() -> None:
    resolver = ManufacturerResolver()
    first = resolver.resolve_with_evidence(
        None, PreAuthEvidence(capabilities={"Manufacturer": ["Axis", "Hikvision"]})
    )
    reversed_order = resolver.resolve_with_evidence(
        None, PreAuthEvidence(capabilities={"Manufacturer": ["Hikvision", "Axis"]})
    )
    assert first.resolved == reversed_order.resolved is None
    assert first.confidence == reversed_order.confidence == "CONFLICTING"
    assert first.conflicts == reversed_order.conflicts == ("Axis", "Hikvision")


def test_f02_weak_model_oem_and_substring_false_positive_do_not_resolve_vendor() -> None:
    resolver = ManufacturerResolver()
    oem = resolver.resolve_with_evidence(
        None, PreAuthEvidence(capabilities={"Model": "HIKVISION OEM-42"})
    )
    false_positive = resolver.resolve_with_evidence(
        None, PreAuthEvidence(capabilities={"XAddr": "/galaxis/device"})
    )
    assert oem.resolved is None and oem.confidence == "UNKNOWN"
    assert false_positive.resolved is None and false_positive.confidence == "UNKNOWN"


def test_manual_hint_alone_guides_selection_but_does_not_confirm_manufacturer() -> None:
    resolution = ManufacturerResolver().resolve_with_evidence("Axis", PreAuthEvidence())
    assert resolution.selected == "Axis"
    assert resolution.declared == "Axis"
    assert resolution.resolved is None
    assert resolution.confidence == "UNKNOWN"


def test_hint_never_overrides_conflicting_strong_observed_manufacturers() -> None:
    resolution = ManufacturerResolver().resolve_with_evidence(
        "Axis", PreAuthEvidence(capabilities={"Manufacturer": ["Axis", "Hikvision"]})
    )
    assert resolution.selected is None
    assert resolution.resolved is None
    assert resolution.confidence == "CONFLICTING"


def test_f02_conflict_skips_vendor_adapter_and_uses_only_generic_onvif_once() -> None:
    class Vendor:
        def __init__(self) -> None:
            self.calls = 0

        def collect(self, _target: CameraTarget) -> CameraResult:
            self.calls += 1
            return CameraResult(
                ip=IP,
                status=CollectionStatus.SUCCESS,
                manufacturer="Axis",
                model="M-1",
                serial="S-1",
            )

    from cam_scanner.cameras.registry import AdapterRegistry

    vendor = Vendor()
    registry = AdapterRegistry()
    registry.register("Axis", vendor)
    generic = _Collector(
        CameraResult(
            ip=IP,
            status=CollectionStatus.SUCCESS,
            manufacturer="Axis",
            model="M-1",
            serial="S-1",
        )
    )
    report = VendorFirstCollector(
        onvif_collector=generic,
        registry=registry,
        discoverer=_Discoverer({"Manufacturer": ["Axis", "Hikvision"]}),
    ).collect_report(CameraTarget(IP, "operator", SECRET))
    assert vendor.calls == 0
    assert generic.calls == 1
    assert report.conflicts == ("manufacturer",)
    assert report.status is CollectionStatus.PARTIAL_SUCCESS


def test_f03_preauth_timeout_is_a_sanitized_attempt_and_keeps_reachability() -> None:
    class Device:
        def GetCapabilities(self, **_kwargs: object) -> object:
            raise TimeoutError(f"timeout secret={SECRET}")

        def GetSystemDateAndTime(self) -> dict[str, str]:
            return {"Time": "synthetic"}

    class Client:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def devicemgmt(self) -> Device:
            return Device()

    evidence, report = OnvifPreAuthDiscoverer(client_factory=Client).discover_with_report(
        CameraTarget(IP, "operator", SECRET)
    )
    assert evidence.has_evidence
    assert [item.operation for item in report.attempts] == [
        "GetCapabilities",
        "GetSystemDateAndTime",
    ]
    assert report.attempts[0].error_category == "READ_TIMEOUT"
    assert report.attempts[1].outcome == "SUCCESS"
    assert report.value_for("onvif_reachable") == "REACHABLE"
    assert SECRET not in repr(report)


@pytest.mark.parametrize(
    ("exception", "stage", "expected"),
    [
        (type("ConnectTimeout", (Exception,), {})(), "CONNECT", "CONNECT_TIMEOUT"),
        (type("ReadTimeout", (Exception,), {})(), "HTTP", "READ_TIMEOUT"),
        (type("TLSFailure", (Exception,), {})(), "CONNECT", "TLS_ERROR"),
        (
            type("UnsupportedAuthMechanism", (Exception,), {})(),
            "AUTH",
            "AUTH_MECHANISM_UNSUPPORTED",
        ),
        (type("EndpointNotFound", (Exception,), {})(), "HTTP", "ENDPOINT_UNSUPPORTED"),
        (
            type("Fault", (Exception,), {"code": "env:Sender"})("fixture"),
            "SOAP",
            "SOAP_FAULT",
        ),
        (ValueError("invalid response"), "PARSE", "INVALID_RESPONSE"),
        (type("DeadlineExceeded", (Exception,), {})(), "HTTP", "DEADLINE_EXCEEDED"),
        (ConnectionRefusedError("fixture"), "CONNECT", "CONNECTION_REFUSED"),
    ],
)
def test_f03_transport_and_protocol_errors_keep_discriminating_categories(
    exception: Exception, stage: str, expected: str
) -> None:
    category, _http_status, _protocol_code = normalize_collection_error(exception, stage=stage)
    assert category == expected


def test_soap_not_authorized_remains_an_uncertain_soap_fault() -> None:
    category, http_status, protocol_code = normalize_collection_error(
        Fault("NotAuthorized"), stage="SOAP"
    )

    assert category == "SOAP_FAULT"
    assert http_status is None
    assert protocol_code == "NotAuthorized"


def test_anonymous_http_401_is_not_reported_as_final_auth_rejection() -> None:
    class HttpFailure(Exception):
        response = type("Response", (), {"status_code": 401})()

    category, http_status, protocol_code = normalize_collection_error(
        HttpFailure(), stage="DISCOVERY", authenticated=False
    )

    assert category == "HTTP_ERROR"
    assert http_status == 401
    assert protocol_code is None


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, "AUTH_REJECTED"),
        (403, "AUTHORIZATION_DENIED"),
        (404, "ENDPOINT_UNSUPPORTED"),
        (500, "HTTP_ERROR"),
    ],
)
def test_f03_http_status_categories_remain_distinct(status: int, expected: str) -> None:
    class HttpFailure(Exception):
        def __init__(self, http_status: int) -> None:
            self.response = type("Response", (), {"status_code": http_status})()

    category, actual_status, _protocol_code = normalize_collection_error(
        HttpFailure(status), stage="HTTP"
    )
    assert category == expected
    assert actual_status == status


def test_attempt_and_report_reprs_exclude_secrets_and_raw_diagnostic_fields() -> None:
    attempt = CollectionAttempt(
        stage="HTTP",
        operation="GetDeviceInformation",
        protocol="ONVIF",
        outcome="FAILED",
        error_category="READ_TIMEOUT",
        metadata={
            "Authorization": SECRET,
            "service": "Device",
            "url": f"https://operator:{SECRET}@camera.local/onvif",
        },
    )
    report = _identity().with_attempt(attempt)
    result = report.to_camera_result(IP)
    diagnostic_text = repr(attempt) + repr(report) + repr(result)
    assert SECRET not in repr(CameraTarget(IP, "operator", SECRET))
    assert SECRET not in diagnostic_text
    assert "operator" not in diagnostic_text
    assert "Authorization" not in diagnostic_text
    assert "camera.local" not in diagnostic_text
    assert attempt.metadata == {"service": "Device"}
    assert len(fields(result)) == 14
    assert "password" not in {item.name for item in fields(result)}


def test_domain_schema_rejects_unapproved_evidence_and_identity_profiles() -> None:
    invalid_factories = (
        lambda: EvidenceRecord(
            field="arbitrary_payload",
            value="data",
            source="FIXTURE",
        ),
        lambda: EvidenceRecord(
            field="manufacturer",
            value="Axis",
            source="FIXTURE",
            confidence="WEAK",
        ),
        lambda: CollectionReport(required_fields=("model",)),
    )
    for factory in invalid_factories:
        try:
            factory()
        except ValueError:
            continue
        raise AssertionError("unapproved evidence schema or identity profile was accepted")


def test_exception_secret_is_not_kept_in_report_result_or_sanitized_log() -> None:
    class RaisingCollector:
        def collect(self, _target: CameraTarget) -> CameraResult:
            raise RuntimeError(
                f"password={SECRET}\nAuthorization: Basic token-value\n"
                f"https://operator:{SECRET}@camera.local/onvif"
            )

    output = StringIO()
    logger = logging.getLogger("p2-secret-sanitization")
    logger.handlers.clear()
    handler = logging.StreamHandler(output)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    service = InventoryService(RaisingCollector(), logger=logger)
    report = service.collect_report(CameraTarget(IP, "operator", SECRET))
    result = report.to_camera_result(IP)
    handler.flush()
    combined = repr(report) + repr(result) + output.getvalue()
    logger.removeHandler(handler)
    handler.close()
    assert SECRET not in combined
    assert "token-value" not in combined
    assert "operator" not in combined
    assert "camera.local" not in combined


def test_inventory_service_integrates_report_into_camera_result() -> None:
    class ReportCollector:
        def collect_report(self, _target: CameraTarget) -> CollectionReport:
            return _identity()

        def collect(self, _target: CameraTarget) -> CameraResult:
            raise AssertionError("canonical service should consume the report")

    result = InventoryService(ReportCollector()).collect_one(CameraTarget(IP, "operator", SECRET))
    assert result.status is CollectionStatus.SUCCESS
    assert result.collection_method is CollectionMethod.ONVIF
    assert result.duration >= 0
