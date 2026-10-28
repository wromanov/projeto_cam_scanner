from __future__ import annotations

import json

import pytest

from cam_scanner.cameras.manufacturers.axis import AxisAdapter
from cam_scanner.cameras.manufacturers.dahua import DahuaAdapter
from cam_scanner.cameras.manufacturers.panasonic import PanasonicAdapter
from cam_scanner.cameras.onvif.adapter import GenericOnvifCollector
from cam_scanner.domain.models import CameraTarget, CollectionStatus

_PANASONIC_PROFILE = "i-pro-command-interface-v1.17:WV-S2531L"


class _Response:
    def __init__(self, status: int, body: bytes) -> None:
        self.status_code = status
        self.headers = {"content-length": str(len(body))}
        self.body = body

    def iter_content(self, chunk_size: int):
        yield self.body

    def close(self) -> None:
        pass


class _Cookies:
    def clear(self) -> None:
        pass


class _Session:
    def __init__(self, *responses: _Response) -> None:
        self.responses = list(responses)
        self.requests: list[tuple[str, str, dict[str, object]]] = []
        self.cookies = _Cookies()
        self.trust_env = True

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def get(self, url: str, **kwargs):
        self.requests.append(("GET", url, kwargs))
        return self.responses.pop(0)

    def post(self, url: str, **kwargs):
        self.requests.append(("POST", url, kwargs))
        return self.responses.pop(0)


def _target() -> CameraTarget:
    return CameraTarget("192.0.2.10", "synthetic-user", "synthetic-password")


def _json(payload: dict[str, object]) -> bytes:
    return json.dumps(payload).encode("utf-8")


class _DeviceService:
    def __init__(self, device_info: dict[str, object]) -> None:
        self.device_info = device_info
        self.calls = 0

    def GetDeviceInformation(self) -> dict[str, object]:
        self.calls += 1
        return self.device_info


class _OnvifClient:
    def __init__(self, service: _DeviceService) -> None:
        self.service = service

    def devicemgmt(self) -> _DeviceService:
        return self.service


@pytest.mark.parametrize("hardware_id", ["HW-VALID-01", None, 17])
def test_onvif_hardware_id_is_preserved_only_when_valid(hardware_id) -> None:
    device_info: dict[str, object] = {
        "Manufacturer": "Example Camera",
        "Model": "Synthetic Model",
        "SerialNumber": "SYN-001",
    }
    if hardware_id is not None:
        device_info["HardwareId"] = hardware_id
    service = _DeviceService(device_info)
    collector = GenericOnvifCollector(
        client_factory=lambda **_kwargs: _OnvifClient(service)
    )

    report = collector.collect_report(_target())
    result = report.to_camera_result("192.0.2.10")

    assert service.calls == 1
    expected_hardware_id = hardware_id if isinstance(hardware_id, str) else None
    assert report.value_for("hardware_id") == expected_hardware_id
    assert result.hardware_id == expected_hardware_id
    assert report.value_for("model") == "Synthetic Model"
    assert report.value_for("serial") == "SYN-001"


@pytest.mark.parametrize("hardware_id", ["00:11:22:33:44:55", None])
def test_axis_hardware_id_comes_only_from_the_selected_public_response(hardware_id) -> None:
    properties: dict[str, str] = {"Brand": "AXIS", "SerialNumber": "AX-001"}
    if hardware_id is not None:
        properties["HardwareID"] = hardware_id
    session = _Session(
        _Response(200, _json({"data": {"apiVersions": ["1.2"]}})),
        _Response(200, _json({"data": {"propertyList": properties}})),
    )

    report = AxisAdapter(session_factory=lambda: session).collect_report(_target())

    assert report.value_for("hardware_id") == hardware_id
    assert len(session.requests) == 2
    assert [json.loads(request[2]["data"]) for request in session.requests] == [
        {"method": "getSupportedVersions"},
        {"apiVersion": "1.2", "method": "getAllUnrestrictedProperties"},
    ]
    assert all("auth" not in request[2] for request in session.requests)
    assert all("Authorization" not in request[2].get("headers", {}) for request in session.requests)


@pytest.mark.parametrize(
    ("raw_mac", "expected_mac"),
    [
        ("001122334455", "00:11:22:33:44:55"),
        ("00:11:22:33:44:55", "00:11:22:33:44:55"),
        ("00-11-22-33-44-55", "00:11:22:33:44:55"),
        (None, None),
        ("00:11-22:33:44:55", None),
        ("00:11:22:33:44:GG", None),
    ],
)
def test_panasonic_mac_variants_preserve_partial_identity(raw_mac, expected_mac) -> None:
    lines = ["NAME=WV-S2531L", "SERIAL=PN-001", "VERSION=2.50", "hardwareVersion=HW-9"]
    if raw_mac is not None:
        lines.append(f"MAC={raw_mac}")
    session = _Session(_Response(200, ("\n".join(lines) + "\n").encode("utf-8")))
    adapter = PanasonicAdapter(
        session_factory=lambda: session,
        profile=_PANASONIC_PROFILE,
    )

    report = adapter.collect_report(_target())
    result = report.to_camera_result("192.0.2.10")

    assert report.status is CollectionStatus.PARTIAL_SUCCESS
    assert report.value_for("mac") == expected_mac
    assert result.mac == expected_mac
    assert report.value_for("model") == "WV-S2531L"
    assert report.value_for("serial") == "PN-001"
    assert report.value_for("firmware") == "2.50"
    assert result.hardware_id is None
    assert len(session.requests) == 1


def test_onvif_device_name_hardware_version_and_unknown_keys_do_not_add_identity_fields() -> None:
    service = _DeviceService(
        {
            "Manufacturer": "Example Camera",
            "Model": "Observed Model",
            "SerialNumber": "ON-001",
            "DeviceName": "invented-hostname.invalid",
            "HardwareVersion": "invented-hardware-id",
            "UnknownVendorKey": "unknown-value",
        }
    )
    collector = GenericOnvifCollector(
        client_factory=lambda **_kwargs: _OnvifClient(service)
    )

    report = collector.collect_report(_target())
    result = report.to_camera_result("192.0.2.10")

    assert result.hostname is None
    assert result.hardware_id is None
    assert report.value_for("model") == "Observed Model"
    assert report.value_for("serial") == "ON-001"


def test_axis_device_name_hardware_version_and_unknown_keys_are_not_mapped() -> None:
    session = _Session(
        _Response(200, _json({"data": {"apiVersions": ["1.2"]}})),
        _Response(
            200,
            _json(
                {
                    "data": {
                        "propertyList": {
                            "Brand": "AXIS",
                            "SerialNumber": "AX-002",
                            "deviceName": "invented-hostname.invalid",
                            "hardwareVersion": "invented-hardware-id",
                            "UnknownVendorKey": "unknown-value",
                        }
                    }
                }
            ),
        ),
    )

    report = AxisAdapter(session_factory=lambda: session).collect_report(_target())
    result = report.to_camera_result("192.0.2.10")

    assert result.hostname is None
    assert result.hardware_id is None
    assert report.value_for("serial") == "AX-002"
    assert len(session.requests) == 2


def test_panasonic_device_name_hardware_version_and_unknown_keys_are_not_mapped() -> None:
    session = _Session(
        _Response(
            200,
            b"NAME=WV-S2531L\nSERIAL=PN-002\nVERSION=2.50\n"
            b"deviceName=invented-hostname.invalid\n"
            b"hardwareVersion=invented-hardware-id\n"
            b"UnknownVendorKey=unknown-value\n",
        )
    )
    adapter = PanasonicAdapter(
        session_factory=lambda: session,
        profile=_PANASONIC_PROFILE,
    )

    report = adapter.collect_report(_target())
    result = report.to_camera_result("192.0.2.10")

    assert result.hostname is None
    assert result.hardware_id is None
    assert report.value_for("model") == "WV-S2531L"
    assert report.value_for("serial") == "PN-002"
    assert report.value_for("firmware") == "2.50"


def test_dahua_hardware_version_device_name_and_unknown_keys_are_not_mapped() -> None:
    session = _Session(
        _Response(
            200,
            b"serialNumber=DH-001\ndeviceType=Observed Model\n"
            b"deviceName=invented-hostname.invalid\n"
            b"hardwareVersion=invented-hardware-id\n"
            b"UnknownVendorKey=unknown-value\n",
        ),
        _Response(200, b"vendor=Dahua\n"),
    )

    report = DahuaAdapter(session_factory=lambda: session).collect_report(_target())
    result = report.to_camera_result("192.0.2.10")

    assert result.hostname is None
    assert result.hardware_id is None
    assert report.value_for("serial") == "DH-001"
    assert report.value_for("model") == "Observed Model"
    assert len(session.requests) == 2
