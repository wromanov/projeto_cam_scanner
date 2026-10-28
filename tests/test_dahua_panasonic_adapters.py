from __future__ import annotations

import pytest
import requests

from cam_scanner.cameras.manufacturers.dahua import DahuaAdapter
from cam_scanner.cameras.manufacturers.panasonic import PanasonicAdapter
from cam_scanner.domain.enums import CollectionMethod, CollectionStatus
from cam_scanner.domain.models import CameraTarget

PANASONIC_TEST_PROFILE = "i-pro-command-interface-v1.17:WV-S2531L"


class _Response:
    def __init__(self, status: int, body: bytes, headers: dict[str, str] | None = None) -> None:
        self.status_code = status
        self.headers = headers or {}
        self._body = body
        self.closed = False

    def iter_content(self, chunk_size: int):
        assert chunk_size == 4096
        yield self._body

    def close(self) -> None:
        self.closed = True


class _Session:
    def __init__(self, *responses: _Response | Exception) -> None:
        self.responses = list(responses)
        self.trust_env = True
        self.requests: list[tuple[str, str, dict[str, object]]] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def get(self, url: str, **kwargs):
        self.requests.append(("GET", url, kwargs))
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def _target() -> CameraTarget:
    return CameraTarget(ip="192.0.2.10", username="operator", password="private-password")


def test_dahua_collects_identity_with_only_the_two_documented_read_operations() -> None:
    system = _Response(
        200,
        b"serialNumber=ABC123\ndeviceType=IPC-HF3300\nhardwareVersion=1.00\n",
    )
    vendor = _Response(200, b"vendor=Dahua\n")
    session = _Session(system, vendor)

    report = DahuaAdapter(session_factory=lambda: session).collect_report(_target())

    assert report.status is CollectionStatus.SUCCESS
    assert {name: report.value_for(name) for name in ("manufacturer", "model", "serial")} == {
        "manufacturer": "Dahua",
        "model": "IPC-HF3300",
        "serial": "ABC123",
    }
    assert report.value_for("firmware") is None
    assert [attempt.operation for attempt in report.attempts] == [
        "GET /cgi-bin/magicBox.cgi getSystemInfo",
        "GET /cgi-bin/magicBox.cgi getVendor",
    ]
    assert [url for _, url, _ in session.requests] == [
        "https://192.0.2.10/cgi-bin/magicBox.cgi?action=getSystemInfo",
        "https://192.0.2.10/cgi-bin/magicBox.cgi?action=getVendor",
    ]
    assert session.trust_env is False
    assert all(kwargs["allow_redirects"] is False for _, _, kwargs in session.requests)
    assert all(kwargs["verify"] is True for _, _, kwargs in session.requests)
    assert system.closed and vendor.closed
    assert report.to_camera_result(_target().ip).collection_method is CollectionMethod.VENDOR_HTTP
    assert {item.protocol for item in report.evidence} == {"HTTPS"}


def test_dahua_preserves_partial_evidence_when_vendor_lookup_fails() -> None:
    session = _Session(
        _Response(200, b"serialNumber=ABC123\ndeviceType=IPC-HF3300\n"),
        _Response(401, b"private-password"),
    )

    report = DahuaAdapter(session_factory=lambda: session).collect_report(_target())

    assert report.status is CollectionStatus.PARTIAL_SUCCESS
    assert report.value_for("model") == "IPC-HF3300"
    assert report.value_for("serial") == "ABC123"
    assert report.value_for("manufacturer") is None
    assert report.attempts[-1].error_category == "AUTH_REJECTED"
    assert "private-password" not in repr(report)


def test_panasonic_getinfo_maps_documented_name_serial_and_version_without_inventing_vendor() -> None:
    response = _Response(200, b"<HTML>\r\nNAME=WV-S2531L\r\nSERIAL=ABC123\r\nVERSION=2.50\r\n</HTML>\r\n")
    session = _Session(response)

    report = PanasonicAdapter(
        session_factory=lambda: session, profile=PANASONIC_TEST_PROFILE
    ).collect_report(_target())

    assert report.status is CollectionStatus.PARTIAL_SUCCESS
    assert report.value_for("manufacturer") is None
    assert report.value_for("model") == "WV-S2531L"
    assert report.value_for("serial") == "ABC123"
    assert report.value_for("firmware") == "2.50"
    assert len(session.requests) == 1
    method, url, kwargs = session.requests[0]
    assert (method, url) == ("GET", "https://192.0.2.10/cgi-bin/getinfo?FILE=1")
    assert kwargs["allow_redirects"] is False
    assert kwargs["verify"] is True
    assert session.trust_env is False
    assert response.closed
    assert {item.operation for item in report.evidence} == {"GET /cgi-bin/getinfo"}
    assert {item.protocol for item in report.evidence} == {"HTTPS"}
    assert report.to_camera_result(_target().ip).collection_method is CollectionMethod.VENDOR_HTTP


def test_panasonic_rejects_malformed_html_wrapper() -> None:
    session = _Session(_Response(200, b"<HTML>\nNAME=WV-S2136L\nSERIAL=ABC123\n"))

    report = PanasonicAdapter(
        session_factory=lambda: session, profile=PANASONIC_TEST_PROFILE
    ).collect_report(_target())

    assert report.status is CollectionStatus.FAILED
    assert report.attempts[-1].error_category == "INVALID_RESPONSE"


def test_credentials_are_target_scoped_and_never_copied_to_evidence() -> None:
    session = _Session(_Response(200, b"NAME=private-password\nSERIAL=ABC123\n"))

    report = PanasonicAdapter(
        session_factory=lambda: session, profile=PANASONIC_TEST_PROFILE
    ).collect_report(_target())

    assert report.status is CollectionStatus.PARTIAL_SUCCESS
    assert report.value_for("model") is None
    assert report.value_for("serial") == "ABC123"
    assert "private-password" not in repr(report)
    assert "private-password" not in repr(report.to_camera_result(_target().ip))
    assert "private-password" not in session.requests[0][1]


@pytest.mark.parametrize("adapter_type", [DahuaAdapter, PanasonicAdapter])
def test_invalid_ip_is_rejected_before_network_request(adapter_type) -> None:
    session = _Session(_Response(200, b"NAME=Model\n"))
    target = CameraTarget(ip="not-an-ip", username="operator", password="private-password")

    report = adapter_type(session_factory=lambda: session).collect_report(target)

    assert report.status is CollectionStatus.FAILED
    assert report.attempts[0].error_category == "INVALID_INPUT"
    assert session.requests == []


@pytest.mark.parametrize("adapter_type", [DahuaAdapter, PanasonicAdapter])
def test_timeout_is_normalized_without_leaking_exception_text(adapter_type) -> None:
    session = _Session(requests.ReadTimeout("private-password in response"))

    adapter = (
        adapter_type(session_factory=lambda: session, profile=PANASONIC_TEST_PROFILE)
        if adapter_type is PanasonicAdapter
        else adapter_type(session_factory=lambda: session)
    )
    report = adapter.collect_report(_target())

    assert report.status is CollectionStatus.FAILED
    assert report.attempts[0].error_category == "READ_TIMEOUT"
    assert "private-password" not in repr(report)
    assert "private-password" not in repr(report.to_camera_result(_target().ip))


@pytest.mark.parametrize("adapter_type", [DahuaAdapter, PanasonicAdapter])
def test_tls_failure_does_not_downgrade_to_http(adapter_type) -> None:
    session = _Session(requests.exceptions.SSLError("certificate validation failed"))

    adapter = (
        adapter_type(session_factory=lambda: session, profile=PANASONIC_TEST_PROFILE)
        if adapter_type is PanasonicAdapter
        else adapter_type(session_factory=lambda: session)
    )
    report = adapter.collect_report(_target())

    assert report.status is CollectionStatus.FAILED
    assert report.attempts[0].error_category == "TLS_ERROR"
    assert len(session.requests) == 1
    assert session.requests[0][1].startswith("https://")
    assert session.requests[0][2]["verify"] is True
