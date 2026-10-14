from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from cam_scanner.cameras.manufacturer import ManufacturerNormalizer
from cam_scanner.cameras.manufacturers.axis import AxisAdapter
from cam_scanner.cameras.manufacturers.bosch import BoschAdapter
from cam_scanner.cameras.manufacturers.dahua import DahuaAdapter
from cam_scanner.cameras.manufacturers.hikvision import HikvisionAdapter
from cam_scanner.cameras.manufacturers.panasonic import PanasonicAdapter
from cam_scanner.cameras.manufacturers.samsung_hanwha import SamsungHanwhaAdapter
from cam_scanner.cameras.preauth import PreAuthEvidence
from cam_scanner.cameras.registry import AdapterRegistry, build_default_registry
from cam_scanner.cameras.strategy import VendorFirstCollector
from cam_scanner.domain.enums import CollectionStatus
from cam_scanner.domain.models import (
    CameraResult,
    CameraTarget,
    CollectionAttempt,
    CollectionReport,
    EvidenceRecord,
)


def test_default_registry_contains_only_the_six_supported_vendor_routes() -> None:
    registry = build_default_registry()

    assert isinstance(registry.get("Axis Communications"), AxisAdapter)
    assert isinstance(registry.get("Hikvision"), HikvisionAdapter)
    assert isinstance(registry.get("Samsung Techwin"), SamsungHanwhaAdapter)
    assert isinstance(registry.get("Dahua"), DahuaAdapter)
    assert isinstance(registry.get("Panasonic"), PanasonicAdapter)
    assert isinstance(registry.get("Bosch"), BoschAdapter)
    assert registry.get("Unlisted Vendor") is None
    assert AdapterRegistry().get("Axis") is None


def test_documented_hanwha_and_ipro_names_resolve_to_registered_families() -> None:
    normalizer = ManufacturerNormalizer()

    assert normalizer.normalize("Hanwha Vision") == "Samsung/Hanwha"
    assert normalizer.normalize("Hanwha Techwin") == "Samsung/Hanwha"
    assert normalizer.normalize("i-PRO") == "Panasonic"


class _Discoverer:
    def discover(self, target: CameraTarget) -> PreAuthEvidence:
        manufacturer = "Axis" if target.ip.endswith(".10") else "Dahua"
        return PreAuthEvidence(capabilities={"Manufacturer": manufacturer})


class _RecordingAdapter:
    def __init__(self, manufacturer: str) -> None:
        self.manufacturer = manufacturer
        self.calls: list[CameraTarget] = []

    def collect_report(self, target: CameraTarget) -> CollectionReport:
        self.calls.append(target)
        return CollectionReport(
            evidence=(
                EvidenceRecord("manufacturer", self.manufacturer, "VENDOR", protocol="HTTP"),
                EvidenceRecord("model", f"{self.manufacturer}-Model", "VENDOR", protocol="HTTP"),
                EvidenceRecord("serial", f"SERIAL-{target.ip}", "VENDOR", protocol="HTTP"),
            ),
            attempts=(
                CollectionAttempt(
                    stage="PARSE",
                    operation="collect_report",
                    protocol="HTTP",
                    outcome="SUCCESS",
                ),
            ),
        )


class _UnusedOnvif:
    def collect(self, _target: CameraTarget) -> CameraResult:
        raise AssertionError("complete vendor identity must not fall back to ONVIF")


def test_single_and_parallel_multi_route_only_to_the_detected_vendor() -> None:
    axis = _RecordingAdapter("Axis")
    dahua = _RecordingAdapter("Dahua")
    registry = AdapterRegistry()
    registry.register("Axis", axis)
    registry.register("Dahua", dahua)
    collector = VendorFirstCollector(
        onvif_collector=_UnusedOnvif(), registry=registry, discoverer=_Discoverer()
    )
    targets = (
        CameraTarget("192.0.2.10", "axis-user", "axis-secret"),
        CameraTarget("192.0.2.11", "dahua-user", "dahua-secret"),
    )

    single = collector.collect(targets[0])
    with ThreadPoolExecutor(max_workers=2) as pool:
        multi = list(pool.map(collector.collect, targets))

    assert single.status is CollectionStatus.SUCCESS
    assert [result.manufacturer for result in multi] == ["Axis", "Dahua"]
    assert [result.serial for result in multi] == ["SERIAL-192.0.2.10", "SERIAL-192.0.2.11"]
    assert [target.password for target in axis.calls] == ["axis-secret", "axis-secret"]
    assert [target.password for target in dahua.calls] == ["dahua-secret"]
    assert all(secret not in repr(result) for result, secret in zip(multi, ("axis-secret", "dahua-secret")))
