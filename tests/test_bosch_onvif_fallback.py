from types import SimpleNamespace

from cam_scanner.cameras.manufacturers.bosch import BoschAdapter
from cam_scanner.cameras.onvif.adapter import GenericOnvifCollector
from cam_scanner.cameras.preauth import PreAuthEvidence
from cam_scanner.cameras.registry import AdapterRegistry
from cam_scanner.cameras.strategy import VendorFirstCollector
from cam_scanner.domain.enums import CollectionStatus
from cam_scanner.domain.models import CameraTarget


class _Discoverer:
    def discover(self, _target: CameraTarget) -> PreAuthEvidence:
        return PreAuthEvidence(capabilities={"Manufacturer": "Bosch"})


class _DeviceService:
    def GetDeviceInformation(self):
        return SimpleNamespace(
            Manufacturer="Bosch",
            Model="FLEXIDOME 5100i",
            SerialNumber="SN-12345",
            FirmwareVersion="9.40.0134",
        )


class _OnvifClient:
    def __init__(self, **_options) -> None:
        pass

    def devicemgmt(self) -> _DeviceService:
        return _DeviceService()


def test_bosch_vendor_gap_skips_io_and_generic_onvif_collects_identity() -> None:
    target = CameraTarget(
        ip="192.0.2.20",
        username="operator",
        password="camera-secret",
    )
    registry = AdapterRegistry()
    registry.register("Bosch", BoschAdapter())
    collector = VendorFirstCollector(
        onvif_collector=GenericOnvifCollector(client_factory=_OnvifClient),
        registry=registry,
        discoverer=_Discoverer(),
    )

    report = collector.collect_report(target)
    result = report.to_camera_result(target.ip)

    assert result.status is CollectionStatus.SUCCESS
    assert result.manufacturer == "Bosch"
    assert result.model == "FLEXIDOME 5100i"
    assert result.serial == "SN-12345"
    assert any(
        attempt.error_category == "ENDPOINT_UNSUPPORTED"
        and attempt.outcome == "SKIPPED"
        for attempt in report.attempts
    )
    assert any(
        attempt.operation == "GetDeviceInformation" and attempt.outcome == "SUCCESS"
        for attempt in report.attempts
    )
    assert "camera-secret" not in repr(report)


def test_bosch_report_marks_gap_without_evidence_or_network_data() -> None:
    report = BoschAdapter().collect_report(
        CameraTarget(ip="192.0.2.21", username="operator", password="camera-secret")
    )

    assert report.evidence == ()
    assert len(report.attempts) == 1
    assert report.attempts[0].error_category == "ENDPOINT_UNSUPPORTED"
    assert report.attempts[0].outcome == "SKIPPED"
    assert report.attempts[0].protocol is None
    assert "camera-secret" not in repr(report)
