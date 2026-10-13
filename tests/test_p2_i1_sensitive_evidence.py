"""Synthetic security regression tests for values returned by ONVIF devices."""
from __future__ import annotations

import logging
from io import StringIO

import pytest

from cam_scanner.application.inventory_service import InventoryService
from cam_scanner.cameras.onvif.adapter import GenericOnvifCollector
from cam_scanner.cameras.preauth import OnvifPreAuthDiscoverer, PreAuthEvidence
from cam_scanner.cameras.strategy import VendorFirstCollector
from cam_scanner.domain.enums import CollectionMethod, CollectionStatus
from cam_scanner.domain.models import (
    CameraResult,
    CameraTarget,
    CollectionReport,
    EvidenceRecord,
    is_valid_evidence_value,
)
from cam_scanner.terminal.ui import TerminalUI

IP = "192.0.2.19"
USERNAME = "TEST_USER_CANARY_001"
PASSWORD = "TEST_PASSWORD_CANARY_001"


class FakeDeviceService:
    def __init__(self, device_info: dict[str, str]) -> None:
        self.device_info = device_info

    def GetDeviceInformation(self) -> dict[str, str]:
        return self.device_info


class FakeClient:
    def __init__(self, device_info: dict[str, str], **_kwargs: object) -> None:
        self.service = FakeDeviceService(device_info)

    def devicemgmt(self) -> FakeDeviceService:
        return self.service


def _collect(
    device_info: dict[str, str], *, target: CameraTarget | None = None
) -> CollectionReport:
    collector = GenericOnvifCollector(
        client_factory=lambda **kwargs: FakeClient(device_info, **kwargs)
    )
    return collector.collect_report(target or CameraTarget(IP, USERNAME, PASSWORD))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("Model", PASSWORD),
        ("SerialNumber", f"SN-{PASSWORD}"),
        ("FirmwareVersion", f"build user={USERNAME} password={PASSWORD}"),
        ("Model", f"https://{USERNAME}:{PASSWORD}@camera.local/model"),
        ("SerialNumber", "https://camera.local/serial"),
        ("FirmwareVersion", f"password={PASSWORD}"),
    ],
)
def test_onvif_values_with_credentials_or_urls_are_rejected(field: str, value: str) -> None:
    wire_name = {
        "Model": "model",
        "SerialNumber": "serial",
        "FirmwareVersion": "firmware",
    }[field]
    report = _collect(
        {
            "Manufacturer": "Hikvision",
            "Model": "Model A",
            "SerialNumber": "SN-42",
            "FirmwareVersion": "1.2.3",
            field: value,
        }
    )
    result = report.to_camera_result(IP)
    assert report.value_for(wire_name) is None
    assert getattr(result, wire_name) is None
    expected_status = (
        CollectionStatus.PARTIAL_SUCCESS
        if wire_name in {"model", "serial"}
        else CollectionStatus.SUCCESS
    )
    assert result.status is expected_status
    combined = repr(report) + repr(result)
    assert USERNAME not in combined
    assert PASSWORD not in combined
    assert "camera.local" not in combined
    assert any(item.error_category == "INVALID_RESPONSE" for item in report.attempts)


def test_unsafe_original_manufacturer_is_discarded_but_other_evidence_survives() -> None:
    report = _collect(
        {
            "Manufacturer": f" Hikvision password={PASSWORD} ",
            "Model": "Model A",
            "SerialNumber": "SN-42",
        }
    )
    result = report.to_camera_result(IP)
    assert result.manufacturer is None
    assert result.manufacturer_original is None
    assert result.model == "Model A"
    assert result.serial == "SN-42"
    assert result.status is CollectionStatus.PARTIAL_SUCCESS
    assert PASSWORD not in repr(report) + repr(result)


def test_unsafe_serial_does_not_erase_valid_manufacturer_and_model() -> None:
    report = _collect(
        {
            "Manufacturer": "Hikvision",
            "Model": "Model A",
            "SerialNumber": PASSWORD,
        }
    )
    result = report.to_camera_result(IP)
    assert result.manufacturer == "Hikvision"
    assert result.model == "Model A"
    assert result.serial is None
    assert result.status is CollectionStatus.PARTIAL_SUCCESS
    assert "serial" not in report.conflicts


def test_safe_original_manufacturer_preserves_exact_whitespace() -> None:
    report = _collect(
        {
            "Manufacturer": "  Hikvision   Communications  ",
            "Model": "Model A",
            "SerialNumber": "SN-42",
        }
    )
    result = report.to_camera_result(IP)
    assert result.manufacturer_original == "  Hikvision   Communications  "
    assert result.manufacturer == "Hikvision Communications"


def test_unsafe_firmware_does_not_invalidate_complete_identity() -> None:
    report = _collect(
        {
            "Manufacturer": "Hikvision",
            "Model": "Model A",
            "SerialNumber": "SN-42",
            "FirmwareVersion": f"{PASSWORD}",
        }
    )
    result = report.to_camera_result(IP)
    assert result.status is CollectionStatus.SUCCESS
    assert result.firmware is None
    assert result.model == "Model A" and result.serial == "SN-42"
    assert PASSWORD not in repr(report) + repr(result)


def test_global_evidence_boundary_rejects_unsafe_values_without_target_context() -> None:
    for value in (
        "password=secret-value",
        "http://user:pass@camera.local/path",
        "username=admin",
    ):
        with pytest.raises(ValueError):
            EvidenceRecord(
                field="serial",
                value=value,
                source="FIXTURE",
                operation="GetDeviceInformation",
            )


def test_pre_authentication_manufacturer_echo_is_not_promoted_to_evidence() -> None:
    class PreAuthService:
        def GetCapabilities(self, **_kwargs: object) -> dict[str, str]:
            return {"Manufacturer": PASSWORD}

        def GetSystemDateAndTime(self) -> object:
            return object()

    class PreAuthClient:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def devicemgmt(self) -> PreAuthService:
            return PreAuthService()

    _evidence, report = OnvifPreAuthDiscoverer(client_factory=PreAuthClient).discover_with_report(
        CameraTarget(IP, USERNAME, PASSWORD)
    )
    assert report.value_for("manufacturer") is None
    assert PASSWORD not in repr(report)


def test_rejected_preauth_manufacturer_is_not_reused_and_generic_fallback_runs() -> None:
    class Discoverer:
        def discover_with_report(self, _target: CameraTarget):
            return (
                PreAuthEvidence(capabilities={"Manufacturer": PASSWORD}),
                CollectionReport(),
            )

    class GenericCollector:
        calls = 0

        def collect_report(self, _target: CameraTarget) -> CollectionReport:
            self.calls += 1
            return _collect(
                {"Manufacturer": "Hikvision", "Model": "Model A", "SerialNumber": "SN-42"}
            )

    generic = GenericCollector()
    combined = VendorFirstCollector(onvif_collector=generic, discoverer=Discoverer())
    report = combined.collect_report(CameraTarget(IP, USERNAME, PASSWORD))
    assert generic.calls == 1
    assert report.status is CollectionStatus.SUCCESS
    assert report.value_for("manufacturer") == "Hikvision"
    assert PASSWORD not in repr(report)


def test_single_projection_and_terminal_output_do_not_disclose_canaries() -> None:
    report = _collect(
        {
            "Manufacturer": "Hikvision",
            "Model": PASSWORD,
            "SerialNumber": "SN-42",
        }
    )
    output = StringIO()
    TerminalUI(output_fn=lambda text: output.write(str(text) + "\n")).render_report(
        report, ip=IP, duration=0.1
    )
    logger = logging.getLogger("p2-sensitive-evidence")
    service_result = InventoryService(
        type("ReportCollector", (), {"collect_report": lambda _self, _target: report})(),
        logger=logger,
    ).collect_one(CameraTarget(IP, USERNAME, PASSWORD))
    combined = repr(report) + repr(service_result) + output.getvalue()
    assert USERNAME not in combined
    assert PASSWORD not in combined
    assert "TEST_" not in output.getvalue()


def test_inventory_boundary_filters_prebuilt_report_and_legacy_result() -> None:
    unsafe_report = CollectionReport(
        evidence=(
            EvidenceRecord(field="manufacturer", value="Hikvision", source="FIXTURE"),
            EvidenceRecord(field="model", value=PASSWORD, source="FIXTURE"),
            EvidenceRecord(field="serial", value="SN-42", source="FIXTURE"),
        )
    )

    class ReportCollector:
        def collect_report(self, _target: CameraTarget) -> CollectionReport:
            return unsafe_report

    projected = InventoryService(ReportCollector()).collect_one(
        CameraTarget(IP, USERNAME, PASSWORD)
    )
    assert projected.model is None
    assert projected.manufacturer == "Hikvision" and projected.serial == "SN-42"
    assert projected.status is CollectionStatus.PARTIAL_SUCCESS
    assert PASSWORD not in repr(projected)

    class LegacyCollector:
        def collect(self, _target: CameraTarget) -> CameraResult:
            return CameraResult(
                ip=IP,
                status=CollectionStatus.SUCCESS,
                manufacturer="Hikvision",
                model=PASSWORD,
                serial="SN-42",
                collection_method=CollectionMethod.ONVIF,
            )

    legacy = InventoryService(LegacyCollector()).collect_one(
        CameraTarget(IP, USERNAME, PASSWORD)
    )
    assert legacy.model is None
    assert legacy.status is CollectionStatus.PARTIAL_SUCCESS
    assert PASSWORD not in repr(legacy)


def test_rejected_evidence_does_not_create_a_false_conflict_or_remove_prior_valid_fact() -> None:
    valid = EvidenceRecord(
        field="serial", value="SN-42", source="FIXTURE", operation="GetDeviceInformation"
    )
    report = CollectionReport(evidence=(valid,))
    with pytest.raises(ValueError):
        EvidenceRecord(
            field="serial",
            value=f"password={PASSWORD}",
            source="FIXTURE",
            operation="GetDeviceInformation",
        )
    assert report.value_for("serial") == "SN-42"
    assert "serial" not in report.conflicts
    assert PASSWORD not in repr(report)


def test_empty_and_placeholder_identity_values_do_not_satisfy_identity_v1() -> None:
    for invalid in ("", "   ", "N/A", "unknown"):
        report = _collect(
            {"Manufacturer": "Hikvision", "Model": "Model A", "SerialNumber": invalid}
        )
        assert report.value_for("serial") is None
        assert report.to_camera_result(IP).status is CollectionStatus.PARTIAL_SUCCESS


def test_urls_with_userinfo_and_plain_urls_are_not_stored_in_reports() -> None:
    for serial in (
        f"rtsp://{USERNAME}:{PASSWORD}@camera.local/stream",
        "https://camera.local/device/serial",
        "www.camera.local/device/serial",
    ):
        report = _collect(
            {"Manufacturer": "Hikvision", "Model": "Model A", "SerialNumber": serial}
        )
        assert report.value_for("serial") is None
        assert "camera.local" not in repr(report)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("model", f"prefix{USERNAME}suffix"),
        ("serial", f"SERIAL-{USERNAME}-TAIL"),
        ("manufacturer", f"Hikvision{USERNAME}"),
        ("firmware", f"build-{USERNAME}-release"),
        ("model", f"prefix{USERNAME.lower()}suffix"),
        ("serial", f"prefix{PASSWORD.lower()}suffix"),
    ],
)
def test_known_credentials_are_rejected_as_case_insensitive_substrings(
    field_name: str, value: str
) -> None:
    wire_names = {
        "manufacturer": "Manufacturer",
        "model": "Model",
        "serial": "SerialNumber",
        "firmware": "FirmwareVersion",
    }
    device_info = {
        "Manufacturer": "Hikvision",
        "Model": "Model A",
        "SerialNumber": "SN-42",
        "FirmwareVersion": "1.2.3",
    }
    device_info[wire_names[field_name]] = value
    report = _collect(device_info)
    result = report.to_camera_result(IP)

    assert report.value_for(field_name) is None
    assert getattr(result, field_name) is None
    if field_name in {"manufacturer", "model", "serial"}:
        assert result.status is CollectionStatus.PARTIAL_SUCCESS
    else:
        assert result.status is CollectionStatus.SUCCESS
    assert USERNAME not in repr(report) + repr(result)
    assert PASSWORD not in repr(report) + repr(result)
    assert any(attempt.error_category == "INVALID_RESPONSE" for attempt in report.attempts)


def test_conservative_short_username_collision_is_rejected_without_diagnostic_value() -> None:
    target = CameraTarget(IP, "cam", PASSWORD)
    report = _collect(
        {
            "Manufacturer": "Hikvision",
            "Model": "Cambridge Camera Model",
            "SerialNumber": "SN-42",
        },
        target=target,
    )
    result = report.to_camera_result(IP)
    diagnostic = repr(report) + (result.error_message or "")
    assert result.model is None
    assert result.status is CollectionStatus.PARTIAL_SUCCESS
    assert "Cambridge Camera Model" not in diagnostic
    assert any(attempt.error_category == "INVALID_RESPONSE" for attempt in report.attempts)


def test_empty_username_does_not_reject_values_by_empty_substring() -> None:
    assert is_valid_evidence_value("model", "Model A", sensitive_values=("", ""))
    assert is_valid_evidence_value("model", "Model A", sensitive_values=("", PASSWORD))


def test_clean_text_fields_remain_valid_with_known_credentials() -> None:
    target = CameraTarget(IP, USERNAME, PASSWORD)
    report = _collect(
        {
            "Manufacturer": "Hikvision",
            "Model": "Model A",
            "SerialNumber": "SN-42",
            "FirmwareVersion": "1.2.3",
        },
        target=target,
    )
    result = report.to_camera_result(IP)
    assert result.status is CollectionStatus.SUCCESS
    assert result.manufacturer == "Hikvision"
    assert result.model == "Model A"
    assert result.serial == "SN-42"
    assert result.firmware == "1.2.3"


def test_prebuilt_report_and_legacy_result_reject_concatenated_username() -> None:
    contaminated = f"prefix{USERNAME}suffix"
    prebuilt = CollectionReport(
        evidence=(
            EvidenceRecord(field="manufacturer", value="Hikvision", source="FIXTURE"),
            EvidenceRecord(field="model", value=contaminated, source="FIXTURE"),
            EvidenceRecord(field="serial", value="SN-42", source="FIXTURE"),
        )
    )
    target = CameraTarget(IP, USERNAME, PASSWORD)
    safe_report = prebuilt.validated_for_target((target.username, target.password))
    assert safe_report.value_for("model") is None
    assert safe_report.value_for("manufacturer") == "Hikvision"
    assert safe_report.value_for("serial") == "SN-42"
    assert safe_report.status is CollectionStatus.PARTIAL_SUCCESS
    assert "model" not in safe_report.conflicts

    mixed_report = prebuilt.with_evidence(
        EvidenceRecord(field="model", value="Model A", source="FIXTURE")
    ).validated_for_target((target.username, target.password))
    assert mixed_report.value_for("model") == "Model A"
    assert "model" not in mixed_report.conflicts
    assert mixed_report.status is CollectionStatus.SUCCESS

    legacy_result = CameraResult(
        ip=IP,
        status=CollectionStatus.SUCCESS,
        manufacturer="Hikvision",
        model=contaminated,
        serial="SN-42",
        collection_method=CollectionMethod.ONVIF,
    )
    legacy_report = CollectionReport.from_camera_result(
        legacy_result,
        sensitive_values=(target.username, target.password),
    )
    projected = legacy_report.to_camera_result(IP)
    assert projected.model is None
    assert projected.status is CollectionStatus.PARTIAL_SUCCESS
    assert USERNAME not in repr(legacy_report) + repr(projected)


@pytest.mark.parametrize("field_name", ["hostname", "manufacturer_original", "hardware_id"])
def test_all_other_public_text_fields_use_the_same_target_credential_filter(
    field_name: str,
) -> None:
    contaminated = f"prefix{USERNAME}suffix"
    target = CameraTarget(IP, USERNAME, PASSWORD)
    report = CollectionReport(
        evidence=(
            EvidenceRecord(field="manufacturer", value="Hikvision", source="FIXTURE"),
            EvidenceRecord(field="model", value="Model A", source="FIXTURE"),
            EvidenceRecord(field="serial", value="SN-42", source="FIXTURE"),
            EvidenceRecord(field=field_name, value=contaminated, source="FIXTURE"),
        )
    ).validated_for_target((target.username, target.password))
    result = report.to_camera_result(IP)
    assert report.value_for(field_name) is None
    assert getattr(result, field_name) is None
    assert result.status is CollectionStatus.SUCCESS
    assert USERNAME not in repr(report) + repr(result)


def test_username_in_unexpected_exception_is_removed_from_captured_logs() -> None:
    log_output = StringIO()
    logger = logging.getLogger("p2-username-log-sanitization")
    logger.handlers.clear()
    handler = logging.StreamHandler(log_output)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    class RaisingCollector:
        def collect(self, _target: CameraTarget) -> CameraResult:
            raise RuntimeError(f"transport failed: prefix{USERNAME}suffix {PASSWORD}")

    result = InventoryService(RaisingCollector(), logger=logger).collect_one(
        CameraTarget(IP, USERNAME, PASSWORD)
    )
    handler.flush()
    captured = repr(result) + log_output.getvalue()
    logger.removeHandler(handler)
    handler.close()
    assert USERNAME not in captured
    assert PASSWORD not in captured


def test_contaminated_username_never_reappears_in_cli_or_diagnostics() -> None:
    target = CameraTarget(IP, USERNAME, PASSWORD)
    contaminated = f"prefix{USERNAME}suffix"
    report = CollectionReport(
        evidence=(
            EvidenceRecord(field="manufacturer", value="Hikvision", source="FIXTURE"),
            EvidenceRecord(field="model", value=contaminated, source="FIXTURE"),
            EvidenceRecord(field="serial", value="SN-42", source="FIXTURE"),
        )
    ).validated_for_target((target.username, target.password))
    output = StringIO()
    TerminalUI(output_fn=lambda text: output.write(str(text) + "\n")).render_report(
        report, ip=IP, duration=0.1
    )
    all_public = repr(report) + repr(report.to_camera_result(IP)) + output.getvalue()
    assert USERNAME not in all_public
    assert PASSWORD not in all_public
    assert "INVALID_RESPONSE" in all_public
    assert contaminated not in all_public


def test_fallback_source_report_cannot_reintroduce_concatenated_username() -> None:
    contaminated = f"prefix{USERNAME}suffix"

    class Discoverer:
        def discover_with_report(self, _target: CameraTarget):
            return PreAuthEvidence(), CollectionReport()

    class FallbackCollector:
        def collect_report(self, _target: CameraTarget) -> CollectionReport:
            return CollectionReport(
                evidence=(
                    EvidenceRecord(field="manufacturer", value="Hikvision", source="FIXTURE"),
                    EvidenceRecord(field="model", value=contaminated, source="FIXTURE"),
                    EvidenceRecord(field="serial", value="SN-42", source="FIXTURE"),
                )
            )

    report = VendorFirstCollector(
        onvif_collector=FallbackCollector(), discoverer=Discoverer()
    ).collect_report(CameraTarget(IP, USERNAME, PASSWORD))
    result = report.to_camera_result(IP)
    assert result.model is None
    assert result.status is CollectionStatus.PARTIAL_SUCCESS
    assert USERNAME not in repr(report) + repr(result)
    assert contaminated not in repr(report) + repr(result)
