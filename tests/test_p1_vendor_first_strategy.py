"""Deterministic routing and pre-authentication coverage for P1-A04."""
from dataclasses import fields

import pytest
from zeep.exceptions import Fault

from cam_scanner.application.inventory_service import InventoryService
from cam_scanner.cameras.preauth import (
    ManufacturerResolver,
    OnvifPreAuthDiscoverer,
    PreAuthEvidence,
)
from cam_scanner.cameras.registry import AdapterRegistry
from cam_scanner.cameras.strategy import VendorFirstCollector
from cam_scanner.domain.enums import CollectionMethod, CollectionStatus, ErrorCode
from cam_scanner.domain.models import CameraResult, CameraTarget


def _result(ip: str, manufacturer: str | None = None) -> CameraResult:
    return CameraResult(
        ip=ip,
        status=CollectionStatus.SUCCESS,
        manufacturer=manufacturer,
        collection_method=CollectionMethod.ONVIF,
    )


def _complete_result(ip: str, manufacturer: str) -> CameraResult:
    return CameraResult(
        ip=ip,
        status=CollectionStatus.SUCCESS,
        manufacturer=manufacturer,
        model="Model A",
        serial="serial-1",
        firmware="1.2.3",
    )


class Discoverer:
    def __init__(self, evidence: PreAuthEvidence, events: list[str]) -> None:
        self.evidence = evidence
        self.events = events

    def discover(self, target: CameraTarget) -> PreAuthEvidence:
        self.events.append("preauth")
        return self.evidence


class RecordingCollector:
    def __init__(self, result: CameraResult | None = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.targets: list[CameraTarget] = []

    def collect(self, target: CameraTarget) -> CameraResult:
        self.targets.append(target)
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


def _target(ip: str = "192.0.2.40", password: str = "secret") -> CameraTarget:
    return CameraTarget(ip=ip, username="camera-user", password=password)


def test_known_manufacturer_uses_registered_vendor_adapter_before_onvif() -> None:
    events: list[str] = []
    target = _target()

    class VendorAdapter:
        def collect(self, received: CameraTarget) -> CameraResult:
            events.append("vendor")
            assert received is target
            return _complete_result(received.ip, "Hikvision")

    registry = AdapterRegistry()
    registry.register("Hikvision", VendorAdapter())
    onvif = RecordingCollector(_result(target.ip))
    collector = VendorFirstCollector(
        onvif_collector=onvif,
        registry=registry,
        discoverer=Discoverer(PreAuthEvidence(capabilities={"Extension": "hikCapabilities"}), events),
    )

    result = collector.collect(target)

    assert events == ["preauth", "vendor"]
    assert onvif.targets == []
    assert result.manufacturer == "Hikvision"


def test_known_manufacturer_without_adapter_falls_back_without_other_vendor_attempts() -> None:
    events: list[str] = []
    looked_up: list[str] = []

    class RecordingRegistry(AdapterRegistry):
        def get(self, manufacturer: str):
            looked_up.append(manufacturer)
            return super().get(manufacturer)

    target = _target()
    onvif = RecordingCollector(_result(target.ip, "Hikvision"))
    collector = VendorFirstCollector(
        onvif_collector=onvif,
        registry=RecordingRegistry(),
        discoverer=Discoverer(PreAuthEvidence(capabilities={"Namespace": "urn:hikvision"}), events),
    )

    result = collector.collect(target)

    assert events == ["preauth"]
    assert looked_up == ["Hikvision"]
    assert onvif.targets == [target]
    assert result.status is CollectionStatus.SUCCESS


def test_registered_vendor_adapter_is_complemented_by_onvif_only_for_missing_p1_fields() -> None:
    target = _target()
    registry = AdapterRegistry()

    class PartialVendorAdapter:
        def collect(self, received: CameraTarget) -> CameraResult:
            return _result(received.ip, "Hikvision")

    registry.register("Hikvision", PartialVendorAdapter())
    onvif = RecordingCollector(
        CameraResult(
            ip=target.ip,
            status=CollectionStatus.SUCCESS,
            manufacturer="Hikvision",
            model="Model A",
            serial="serial-1",
            firmware="1.2.3",
            collection_method=CollectionMethod.ONVIF,
        )
    )
    collector = VendorFirstCollector(
        onvif_collector=onvif,
        registry=registry,
        discoverer=Discoverer(PreAuthEvidence(capabilities={"Extension": "hikCapabilities"}), []),
    )

    result = collector.collect(target)

    assert result.manufacturer == "Hikvision"
    assert result.model == "Model A"
    assert result.serial == "serial-1"
    assert result.firmware == "1.2.3"
    assert onvif.targets == [target]


def test_onvif_manufacturer_mismatch_is_reported_without_replacing_vendor_result(caplog) -> None:
    target = _target()
    registry = AdapterRegistry()

    class PartialVendorAdapter:
        def collect(self, received: CameraTarget) -> CameraResult:
            return _result(received.ip, "Hikvision")

    registry.register("Hikvision", PartialVendorAdapter())
    onvif = RecordingCollector(
        CameraResult(
            ip=target.ip,
            status=CollectionStatus.SUCCESS,
            manufacturer="Dahua",
            model="Model A",
            serial="serial-1",
            firmware="1.2.3",
            collection_method=CollectionMethod.ONVIF,
        )
    )
    collector = VendorFirstCollector(
        onvif_collector=onvif,
        registry=registry,
        discoverer=Discoverer(PreAuthEvidence(capabilities={"Extension": "hikCapabilities"}), []),
    )

    result = collector.collect(target)

    assert result.manufacturer == "Hikvision"
    assert result.model == "Model A"
    assert "Manufacturer evidence mismatch detected" in caplog.text


def test_absent_manufacturer_runs_preauth_before_generic_onvif() -> None:
    events: list[str] = []
    target = _target()

    class OrderedOnvif(RecordingCollector):
        def collect(self, received: CameraTarget) -> CameraResult:
            events.append("onvif")
            return super().collect(received)

    onvif = OrderedOnvif(_result(target.ip, "Generic Camera"))
    collector = VendorFirstCollector(
        onvif_collector=onvif,
        discoverer=Discoverer(PreAuthEvidence(), events),
    )

    assert collector.collect(target).manufacturer == "Generic Camera"
    assert events == ["preauth", "onvif"]


@pytest.mark.parametrize(
    ("capability", "expected"),
    [
        ("hikCapabilities", "Hikvision"),
        ("urn:axis:camera", "Axis"),
        ("urn:hanwha:camera", "Samsung/Hanwha"),
        ("vendor=Dahua", "Dahua"),
        ("urn:panasonic:camera", "Panasonic"),
        ("urn:bosch:camera", "Bosch"),
    ],
)
def test_fingerprint_resolves_only_vendor_supported_by_structural_evidence(
    capability: str, expected: str
) -> None:
    resolver = ManufacturerResolver()
    assert resolver.resolve(None, PreAuthEvidence(capabilities={"Extension": capability})) == expected


def test_fingerprint_reads_onvif_compound_values_without_vendor_specific_parsing() -> None:
    class OnvifValue:
        def __init__(self) -> None:
            self.__values__ = {"Extension": {"hikCapabilities": {"XAddr": "http://camera/onvif"}}}

    assert ManufacturerResolver().detect(PreAuthEvidence(capabilities=OnvifValue())) == "Hikvision"


def test_unknown_manufacturer_uses_generic_onvif() -> None:
    target = _target()
    onvif = RecordingCollector(_result(target.ip, "Unlisted Camera"))
    collector = VendorFirstCollector(onvif_collector=onvif, discoverer=Discoverer(PreAuthEvidence(), []))

    assert collector.collect(target).manufacturer == "Unlisted Camera"
    assert len(onvif.targets) == 1


def test_declared_manufacturer_mismatch_is_detected_without_silent_replacement() -> None:
    resolution = ManufacturerResolver().resolve_with_evidence(
        "Axis", PreAuthEvidence(capabilities={"Namespace": "urn:hikvision"})
    )

    assert resolution.selected == "Axis"
    assert resolution.detected == "Hikvision"
    assert resolution.mismatch


def test_auth_failure_after_valid_preauth_evidence_returns_partial_success() -> None:
    target = _target()
    onvif = RecordingCollector(error=Fault("NotAuthorized"))
    collector = VendorFirstCollector(
        onvif_collector=onvif,
        discoverer=Discoverer(PreAuthEvidence(system_date_time={"DateTime": "read-only"}), []),
    )

    result = collector.collect(target)

    assert result.status is CollectionStatus.PARTIAL_SUCCESS
    assert result.error_code is ErrorCode.AUTH_ERROR
    assert result.manufacturer is None


def test_wrapped_onvif_auth_error_after_preauth_still_returns_partial_success() -> None:
    from onvif.utils.exceptions import ONVIFOperationException

    target = _target()
    onvif = RecordingCollector(error=ONVIFOperationException("GetDeviceInformation", Fault("NotAuthorized")))
    collector = VendorFirstCollector(
        onvif_collector=onvif,
        discoverer=Discoverer(PreAuthEvidence(capabilities={"Extension": "hikCapabilities"}), []),
    )

    result = collector.collect(target)

    assert result.status is CollectionStatus.PARTIAL_SUCCESS
    assert result.error_code is ErrorCode.AUTH_ERROR
    assert result.manufacturer == "Hikvision"


def test_no_preauth_evidence_and_failed_collection_remains_failed() -> None:
    target = _target()
    collector = VendorFirstCollector(
        onvif_collector=RecordingCollector(error=Fault("NotAuthorized")),
        discoverer=Discoverer(PreAuthEvidence(), []),
    )

    result = InventoryService(collector).collect_one(target)

    assert result.status is CollectionStatus.FAILED
    assert result.error_code is ErrorCode.AUTH_ERROR


def test_each_collection_keeps_credentials_bound_to_their_own_target() -> None:
    received: list[CameraTarget] = []

    class VendorAdapter:
        def collect(self, target: CameraTarget) -> CameraResult:
            received.append(target)
            return _complete_result(target.ip, "Axis")

    registry = AdapterRegistry()
    registry.register("Axis", VendorAdapter())
    collector = VendorFirstCollector(
        registry=registry,
        discoverer=Discoverer(PreAuthEvidence(capabilities={"Namespace": "axis"}), []),
    )
    first, second = _target("192.0.2.41", "first-secret"), _target("192.0.2.42", "second-secret")

    collector.collect(first)
    collector.collect(second)

    assert received == [first, second]
    assert [item.password for item in received] == ["first-secret", "second-secret"]
    assert all("secret" not in repr(item) for item in received)


def test_failed_fallback_never_exposes_password_or_adds_result_fields() -> None:
    secret = "UniqueP1Secret"
    target = _target(password=secret)
    collector = VendorFirstCollector(
        onvif_collector=RecordingCollector(error=Fault("NotAuthorized")),
        discoverer=Discoverer(PreAuthEvidence(capabilities={"Extension": "hikCapabilities"}), []),
    )

    result = collector.collect(target)

    assert result.status is CollectionStatus.PARTIAL_SUCCESS
    assert secret not in repr(target)
    assert secret not in repr(result)
    assert [item.name for item in fields(result)] == [
        "ip", "status", "hostname", "manufacturer", "manufacturer_original", "model", "serial",
        "firmware", "hardware_id", "mac", "error_code", "error_message", "collection_method", "duration",
    ]


def test_preauth_discovery_uses_no_target_credentials_and_calls_only_read_methods() -> None:
    calls: list[str] = []
    options: dict[str, object] = {}

    class Device:
        def GetCapabilities(self, **kwargs: object) -> dict[str, str]:
            calls.append("GetCapabilities")
            assert kwargs == {"Category": "All"}
            return {"Extension": "hikCapabilities"}

        def GetSystemDateAndTime(self) -> dict[str, str]:
            calls.append("GetSystemDateAndTime")
            return {"Time": "read-only"}

    class Client:
        def __init__(self, **kwargs: object) -> None:
            options.update(kwargs)

        def devicemgmt(self) -> Device:
            return Device()

    evidence = OnvifPreAuthDiscoverer(client_factory=Client).discover(_target())

    assert "username" not in options
    assert "password" not in options
    assert calls == ["GetCapabilities", "GetSystemDateAndTime"]
    assert evidence.has_evidence


def test_try_all_vendor_logins_is_not_present_as_a_strategy() -> None:
    from pathlib import Path

    source = Path(__file__).parents[1] / "src" / "cam_scanner" / "cameras" / "strategy.py"
    assert "TRY_ALL_VENDOR_LOGINS" not in source.read_text(encoding="utf-8")
