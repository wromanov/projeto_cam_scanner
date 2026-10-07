"""Tests for the single read-only ONVIF operation in P1."""
import logging

from cam_scanner.cameras.onvif.adapter import GenericOnvifCollector, _suppress_dependency_logs
from cam_scanner.domain.enums import CollectionMethod, CollectionStatus
from cam_scanner.domain.models import CameraTarget


def test_generic_collector_explicitly_calls_get_device_information() -> None:
    calls: list[str] = []

    class FakeDeviceService:
        def GetDeviceInformation(self) -> dict[str, str]:
            calls.append("GetDeviceInformation")
            return {
                "Manufacturer": "  Example   Cameras  ",
                "Model": "Model A",
                "SerialNumber": "serial-1",
                "FirmwareVersion": "1.2.3",
            }

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            self.options = kwargs

        def devicemgmt(self) -> FakeDeviceService:
            return FakeDeviceService()

    result = GenericOnvifCollector(client_factory=FakeClient).collect(
        CameraTarget(ip="192.0.2.10", username="operator", password="secret")
    )

    assert calls == ["GetDeviceInformation"]
    assert result.status is CollectionStatus.SUCCESS
    assert result.collection_method is CollectionMethod.ONVIF
    assert result.manufacturer == "Example Cameras"
    assert result.manufacturer_original == "  Example   Cameras  "
    assert result.model == "Model A"
    assert result.serial == "serial-1"
    assert result.firmware == "1.2.3"
    assert result.hardware_id is None
    assert result.mac is None


def test_default_client_disables_disk_cache_and_uses_request_timeout(monkeypatch) -> None:
    from onvif import CacheMode

    captured: dict[str, object] = {}

    class FakeDeviceService:
        def GetDeviceInformation(self) -> dict[str, str]:
            return {}

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

        def devicemgmt(self) -> FakeDeviceService:
            return FakeDeviceService()

    import onvif

    monkeypatch.setattr(onvif, "ONVIFClient", FakeClient)
    GenericOnvifCollector().collect(
        CameraTarget(ip="192.0.2.10", username="operator", password="secret")
    )

    assert captured["cache"] is CacheMode.NONE
    assert captured["timeout"] == 7
    assert captured["port"] == 80


def test_dependency_logs_are_suppressed_before_collection(monkeypatch) -> None:
    dependency_loggers = [logging.getLogger(name) for name in ("onvif", "zeep", "requests", "urllib3")]
    for dependency_logger in dependency_loggers:
        monkeypatch.setattr(dependency_logger, "level", logging.NOTSET)
        monkeypatch.setattr(dependency_logger, "propagate", True)

    _suppress_dependency_logs()

    assert all(logger.level > logging.CRITICAL for logger in dependency_loggers)
    assert all(not logger.propagate for logger in dependency_loggers)
