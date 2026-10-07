"""Generic, read-only ONVIF collector for the P1 device information call."""
import logging
from collections.abc import Callable, Mapping
from typing import Any

from cam_scanner.cameras.collector import CameraCollector
from cam_scanner.cameras.manufacturer import ManufacturerNormalizer
from cam_scanner.domain.enums import CollectionMethod, CollectionStatus
from cam_scanner.domain.models import CameraResult, CameraTarget


class GenericOnvifCollector(CameraCollector):
    """Read P1 device information; the client also performs read-only service discovery."""

    def __init__(
        self,
        client_factory: Callable[..., Any] | None = None,
        timeout_seconds: int = 7,
    ) -> None:
        self._client_factory = client_factory
        self._timeout_seconds = timeout_seconds
        self._manufacturer_normalizer = ManufacturerNormalizer()

    def collect(self, target: CameraTarget) -> CameraResult:
        _suppress_dependency_logs()
        client_factory = self._client_factory
        client_options: dict[str, object] = {
            "host": target.ip,
            "port": 80,
            "username": target.username,
            "password": target.password,
            "timeout": self._timeout_seconds,
        }
        if client_factory is None:
            from onvif import CacheMode, ONVIFClient

            client_factory = ONVIFClient
            client_options["cache"] = CacheMode.NONE

        client = client_factory(**client_options)
        device_service = client.devicemgmt()
        device_info = device_service.GetDeviceInformation()

        manufacturer_original = self._read_field(device_info, "Manufacturer")
        return CameraResult(
            ip=target.ip,
            status=CollectionStatus.SUCCESS,
            manufacturer=self._manufacturer_normalizer.normalize(manufacturer_original),
            manufacturer_original=manufacturer_original,
            model=self._read_field(device_info, "Model"),
            serial=self._read_field(device_info, "SerialNumber"),
            firmware=self._read_field(device_info, "FirmwareVersion"),
            collection_method=CollectionMethod.ONVIF,
        )

    @staticmethod
    def _read_field(device_info: object, name: str) -> str | None:
        if isinstance(device_info, Mapping):
            value = device_info.get(name)
        else:
            value = getattr(device_info, name, None)
        if not isinstance(value, str):
            return None
        return value


def _suppress_dependency_logs() -> None:
    """Keep raw ONVIF/transport diagnostics from reaching terminal or log handlers."""
    for logger_name in ("onvif", "zeep", "requests", "urllib3"):
        dependency_logger = logging.getLogger(logger_name)
        dependency_logger.setLevel(logging.CRITICAL + 1)
        dependency_logger.propagate = False
