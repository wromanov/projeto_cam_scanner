from __future__ import annotations

import json

import pytest
import requests

from cam_scanner.cameras.manufacturers.axis import AxisAdapter
from cam_scanner.cameras.manufacturers.samsung_hanwha import SamsungHanwhaAdapter
from cam_scanner.domain.enums import CollectionStatus
from cam_scanner.domain.models import CameraTarget


class _Response:
    def __init__(self, status: int, body: bytes, headers: dict[str, str] | None = None) -> None:
        self.status_code = status
        self.headers = headers or {}
        self._body = body
        self.closed = False

    def iter_content(self, chunk_size: int):
        assert chunk_size == 8192
        yield self._body

    def close(self) -> None:
        self.closed = True


class _Session:
    def __init__(self, *responses: _Response | Exception) -> None:
        self.responses = list(responses)
        self.trust_env = True
        self.request: tuple[str, str, dict[str, object]] | None = None
        self.requests: list[tuple[str, str, dict[str, object]]] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def _send(self, method: str, url: str, **kwargs):
        self.request = (method, url, kwargs)
        self.requests.append(self.request)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def post(self, url: str, **kwargs):
        return self._send("POST", url, **kwargs)

    def get(self, url: str, **kwargs):
        return self._send("GET", url, **kwargs)


def _factory(session: _Session):
    return lambda: session


def _target() -> CameraTarget:
    return CameraTarget(ip="192.0.2.10", username="operator", password="private-password")


def test_axis_uses_only_documented_bdi_post_and_records_identity_and_firmware() -> None:
    versions = _Response(200, b'{"data":{"apiVersions":["1.2"]}}')
    properties = _Response(
        200,
        json.dumps(
            {
                "data": {
                    "propertyList": {
                        "Brand": "AXIS",
                        "ProdFullName": "AXIS Q3505 Mk II Fixed Dome Network Camera",
                        "ProdNbr": "Q3505 Mk II",
                        "SerialNumber": "ACCC8E78B977",
                        "Version": "8.20.1",
                    }
                }
            }
        ).encode(),
    )
    session = _Session(versions, properties)

    report = AxisAdapter(session_factory=_factory(session)).collect_report(_target())

    assert report.status is CollectionStatus.SUCCESS
    assert {field: report.value_for(field) for field in ("manufacturer", "model", "serial", "firmware")} == {
        "manufacturer": "AXIS",
        "model": "AXIS Q3505 Mk II Fixed Dome Network Camera",
        "serial": "ACCC8E78B977",
        "firmware": "8.20.1",
    }
    assert session.trust_env is False
    assert len(session.requests) == 2
    first, second = session.requests
    assert (first[0], first[1]) == (
        "POST", "https://192.0.2.10/axis-cgi/basicdeviceinfo.cgi"
    )
    assert json.loads(first[2]["data"]) == {"method": "getSupportedVersions"}
    assert "auth" not in first[2]
    assert (second[0], second[1]) == (
        "POST", "https://192.0.2.10/axis-cgi/basicdeviceinfo.cgi"
    )
    assert json.loads(second[2]["data"]) == {
        "apiVersion": "1.2", "method": "getAllUnrestrictedProperties"
    }
    assert "auth" not in second[2]
    assert session.request is not None
    assert session.request[2]["allow_redirects"] is False
    assert versions.closed and properties.closed
    assert all(record.operation == "POST /axis-cgi/basicdeviceinfo.cgi getAllUnrestrictedProperties" for record in report.evidence)
    assert {record.protocol for record in report.evidence} == {"HTTPS"}


def test_hanwha_does_not_infer_manufacturer_from_endpoint_and_preserves_partial_identity() -> None:
    response = _Response(
        200,
        b'{"Model":"XNV-9083R","SerialNumber":"ZRG070GR50000KE",'
        b'"FirmwareVersion":"2.23.08_20250718_R29"}',
    )
    session = _Session(response)

    report = SamsungHanwhaAdapter(session_factory=_factory(session)).collect_report(_target())

    assert report.status is CollectionStatus.PARTIAL_SUCCESS
    assert report.value_for("manufacturer") is None
    assert report.value_for("model") == "XNV-9083R"
    assert report.value_for("serial") == "ZRG070GR50000KE"
    assert report.value_for("firmware") == "2.23.08_20250718_R29"
    assert session.request is not None
    method, url, kwargs = session.request
    assert (method, url) == (
        "GET",
        "https://192.0.2.10/stw-cgi/system.cgi?msubmenu=deviceinfo&action=view",
    )
    assert kwargs["allow_redirects"] is False
    assert all(record.operation == "GET /stw-cgi/system.cgi deviceinfo view" for record in report.evidence)
    assert {record.protocol for record in report.evidence} == {"HTTPS"}


def test_hanwha_accepts_explicit_manufacturer_from_device_payload() -> None:
    session = _Session(
        _Response(
            200,
            b'Manufacturer=Hanwha Vision\nModel=TNM-C4940TDR\nSerialNumber=ABC123\n',
        )
    )

    report = SamsungHanwhaAdapter(session_factory=_factory(session)).collect_report(_target())

    assert report.status is CollectionStatus.SUCCESS
    assert report.value_for("manufacturer") == "Hanwha Vision"
    assert report.value_for("model") == "TNM-C4940TDR"
    assert report.value_for("serial") == "ABC123"


@pytest.mark.parametrize(
    ("adapter_type", "method", "operation"),
    [
        (SamsungHanwhaAdapter, "GET", "GET /stw-cgi/system.cgi deviceinfo view"),
    ],
)
def test_auth_failure_is_normalized_and_credentials_stay_target_scoped(adapter_type, method, operation) -> None:
    session = _Session(_Response(401, b"private-password"))

    report = adapter_type(session_factory=_factory(session)).collect_report(_target())

    assert report.status is CollectionStatus.FAILED
    assert len(report.attempts) == 1
    attempt = report.attempts[0]
    assert attempt.error_category == "AUTH_REJECTED"
    assert attempt.operation == operation
    assert attempt.authentication_mechanism == "HTTP_DIGEST"
    assert "private-password" not in repr(report)
    assert "private-password" not in repr(report.to_camera_result("192.0.2.10"))
    assert session.request is not None
    assert session.request[0] == method
    assert "private-password" not in session.request[1]
    auth = session.request[2]["auth"]
    assert auth.username == "operator"
    assert auth.password == "private-password"


def test_axis_public_401_does_not_replay_with_credentials() -> None:
    session = _Session(_Response(401, b"private-password"))

    report = AxisAdapter(session_factory=_factory(session)).collect_report(_target())

    assert report.status is CollectionStatus.FAILED
    assert len(report.attempts) == 1
    assert report.attempts[0].error_category == "HTTP_ERROR"
    assert report.attempts[0].operation == (
        "POST /axis-cgi/basicdeviceinfo.cgi getSupportedVersions"
    )
    assert report.attempts[0].authentication_mechanism == "NONE"
    assert "private-password" not in repr(report)
    assert len(session.requests) == 1
    assert "auth" not in session.requests[0][2]


def test_timeout_error_does_not_leak_transport_message() -> None:
    session = _Session(requests.ReadTimeout("private-password in transport message"))

    report = AxisAdapter(session_factory=_factory(session)).collect_report(_target())

    assert report.status is CollectionStatus.FAILED
    assert report.attempts[0].error_category == "READ_TIMEOUT"
    assert "private-password" not in repr(report)
    assert "private-password" not in repr(report.to_camera_result("192.0.2.10"))


@pytest.mark.parametrize("adapter_type", [AxisAdapter, SamsungHanwhaAdapter])
def test_oversized_response_is_rejected_and_response_closed(adapter_type) -> None:
    response = _Response(200, b"x" * (64 * 1024 + 1))
    session = _Session(response)

    report = adapter_type(session_factory=_factory(session)).collect_report(_target())

    assert report.status is CollectionStatus.FAILED
    assert report.attempts[0].error_category == "INVALID_RESPONSE"
    assert response.closed


@pytest.mark.parametrize("adapter_type", [AxisAdapter, SamsungHanwhaAdapter])
def test_unexpected_json_shape_is_sanitized_as_invalid_response(adapter_type) -> None:
    session = _Session(_Response(200, b"[]"))

    report = adapter_type(session_factory=_factory(session)).collect_report(_target())

    assert report.status is CollectionStatus.FAILED
    assert report.attempts[0].error_category == "INVALID_RESPONSE"


@pytest.mark.parametrize("adapter_type", [AxisAdapter, SamsungHanwhaAdapter])
def test_invalid_ip_is_rejected_before_network_request(adapter_type) -> None:
    session = _Session(_Response(200, b"{}"))
    target = CameraTarget(ip="not-an-ip", username="operator", password="private-password")

    report = adapter_type(session_factory=_factory(session)).collect_report(target)

    assert report.status is CollectionStatus.FAILED
    assert report.attempts[0].error_category == "INVALID_INPUT"
    assert session.request is None
