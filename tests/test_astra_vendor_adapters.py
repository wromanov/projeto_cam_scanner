from __future__ import annotations

import json

from cam_scanner.cameras.manufacturers.axis import AxisAdapter
from cam_scanner.cameras.manufacturers.panasonic import PanasonicAdapter
from cam_scanner.domain.models import CameraTarget, CollectionStatus


class _Response:
    def __init__(self, status: int, body: bytes) -> None:
        self.status_code = status
        self.headers = {"content-length": str(len(body))}
        self.body = body
        self.closed = False

    def iter_content(self, chunk_size: int):
        yield self.body

    def close(self) -> None:
        self.closed = True


class _Cookies:
    def clear(self) -> None:
        pass


class _Session:
    def __init__(self, *responses: _Response) -> None:
        self.responses = list(responses)
        self.requests: list[tuple[str, str, dict]] = []
        self.cookies = _Cookies()
        self.trust_env = True

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def post(self, url: str, **kwargs):
        self.requests.append(("POST", url, kwargs))
        return self.responses.pop(0)

    def get(self, url: str, **kwargs):
        self.requests.append(("GET", url, kwargs))
        return self.responses.pop(0)


def _target() -> CameraTarget:
    return CameraTarget("192.0.2.10", "admin", "secret")


def _json(payload: dict) -> bytes:
    return json.dumps(payload).encode()


def test_axis_uses_only_anonymous_supported_version_12_flow() -> None:
    session = _Session(
        _Response(200, _json({"data": {"apiVersions": ["1.0", "1.2"]}})),
        _Response(200, _json({"data": {"propertyList": {
            "Brand": "AXIS", "SerialNumber": "ABC", "Version": "1.0",
            "ProdFullName": "Camera", "HardwareID": "00:11:22:33:44:55",
        }}})),
    )

    report = AxisAdapter(session_factory=lambda: session).collect_report(_target())

    assert report.status is CollectionStatus.SUCCESS
    assert len(session.requests) == 2
    assert [json.loads(req[2]["data"]) for req in session.requests] == [
        {"method": "getSupportedVersions"},
        {"apiVersion": "1.2", "method": "getAllUnrestrictedProperties"},
    ]
    assert all("auth" not in req[2] and "cookies" not in req[2] for req in session.requests)
    assert all("Authorization" not in req[2].get("headers", {}) for req in session.requests)
    assert all(req[2]["verify"] is True and req[2]["allow_redirects"] is False for req in session.requests)
    assert report.value_for("manufacturer") == "AXIS"


def test_axis_public_401_does_not_replay_or_try_credentials() -> None:
    session = _Session(_Response(401, b""), _Response(200, b"must not be read"))

    report = AxisAdapter(session_factory=lambda: session).collect_report(_target())

    assert report.status is CollectionStatus.FAILED
    assert report.attempts[0].error_category == "HTTP_ERROR"
    assert report.attempts[0].authentication_mechanism == "NONE"
    assert len(session.requests) == 1


def test_axis_200_vendor_error_is_fail_closed_without_properties_request() -> None:
    session = _Session(_Response(200, _json({"error": {"code": 2001, "message": "private"}})))

    report = AxisAdapter(session_factory=lambda: session).collect_report(_target())

    assert report.status is CollectionStatus.FAILED
    assert report.attempts[0].error_category == "AUTHORIZATION_DENIED"
    assert len(session.requests) == 1
    assert "private" not in repr(report)


def test_panasonic_without_exact_profile_skips_without_request() -> None:
    session = _Session()

    report = PanasonicAdapter(session_factory=lambda: session).collect_report(_target())

    assert report.status is CollectionStatus.FAILED
    assert report.attempts[0].outcome == "SKIPPED"
    assert report.attempts[0].error_category == "ENDPOINT_UNSUPPORTED"
    assert not session.requests


def test_panasonic_exact_profile_maps_partial_identity_and_returned_mac() -> None:
    session = _Session(_Response(200, b"NAME=WV-S2531L\nSERIAL=ABC123\nVERSION=2.50\nMAC=00:11:22:33:44:55\n"))

    report = PanasonicAdapter(
        session_factory=lambda: session,
        profile="i-pro-command-interface-v1.17:WV-S2531L",
    ).collect_report(_target())

    assert report.status is CollectionStatus.PARTIAL_SUCCESS
    assert report.value_for("model") == "WV-S2531L"
    assert report.value_for("serial") == "ABC123"
    assert report.value_for("firmware") == "2.50"
    assert report.value_for("mac") == "00:11:22:33:44:55"
    assert report.value_for("manufacturer") is None
    assert len(session.requests) == 1
