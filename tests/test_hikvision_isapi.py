"""Offline transport and integration coverage for the approved ISAPI PoC."""
from __future__ import annotations

from urllib.parse import urlsplit

import pytest
import requests
from requests.adapters import BaseAdapter

from cam_scanner.cameras.manufacturers.hikvision import HikvisionAdapter, _parse_device_info
from cam_scanner.cameras.preauth import PreAuthEvidence
from cam_scanner.cameras.registry import AdapterRegistry
from cam_scanner.cameras.strategy import VendorFirstCollector
from cam_scanner.domain.enums import CollectionMethod, CollectionStatus
from cam_scanner.domain.models import CameraResult, CameraTarget

_DEVICE_INFO = b"""<?xml version='1.0' encoding='UTF-8'?>
<DeviceInfo xmlns='http://www.hikvision.com/ver20/XMLSchema'>
  <deviceName>Front Door</deviceName>
  <deviceID>device-1</deviceID>
  <model>DS-KD8003</model>
  <serialNumber>serial-123</serialNumber>
  <macAddress>00:11:22:33:44:55</macAddress>
  <firmwareVersion>3.7.1</firmwareVersion>
  <manufacturer>Hikvision</manufacturer>
</DeviceInfo>"""
_DIGEST_CHALLENGE = 'Digest realm="camera", nonce="abc123", qop="auth", algorithm=MD5'


def _target(ip: str = "192.0.2.10", username: str = "operator", password: str = "safe-pass"):
    return CameraTarget(ip=ip, username=username, password=password)


def _response(request, status: int, body: bytes = b"", headers: dict[str, str] | None = None):
    response = requests.Response()
    response.status_code = status
    response.headers.update(headers or {})
    response._content = body
    response._content_consumed = True
    response.url = request.url
    response.request = request
    return response


def _adapter(handler):
    sent: list[requests.PreparedRequest] = []

    class OfflineAdapter(BaseAdapter):
        def send(self, request, **_kwargs):
            sent.append(request)
            response = handler(request)
            response.connection = self
            return response

        def close(self) -> None:
            return None

    def session_factory() -> requests.Session:
        session = requests.Session()
        session.mount("https://", OfflineAdapter())
        return session

    return HikvisionAdapter(session_factory=session_factory), sent


def test_digest_handshake_reads_only_approved_identity_endpoint_and_parses_xml() -> None:
    def handler(request):
        if "authorization" not in request.headers:
            return _response(
                request,
                401,
                headers={"WWW-Authenticate": _DIGEST_CHALLENGE},
            )
        return _response(request, 200, _DEVICE_INFO)

    adapter, sent = _adapter(handler)
    report = adapter.collect_report(_target())
    result = report.to_camera_result("192.0.2.10")

    assert [request.method for request in sent] == ["GET", "GET"]
    assert all(urlsplit(request.url).path == "/ISAPI/System/deviceInfo" for request in sent)
    assert urlsplit(sent[0].url).scheme == "https"
    assert urlsplit(sent[0].url).port is None  # HTTPS default port 443
    assert "authorization" not in sent[0].headers
    assert sent[1].headers["Authorization"].startswith("Digest ")
    assert isinstance(sent[1].hooks.get("response"), list)
    assert result.status is CollectionStatus.SUCCESS
    assert result.collection_method is CollectionMethod.HIKVISION_ISAPI
    assert result.manufacturer == "Hikvision"
    assert result.hostname is None
    assert result.model == "DS-KD8003"
    assert result.serial == "serial-123"
    assert result.firmware == "3.7.1"
    assert any(item.field == "model" for item in report.evidence)
    assert report.attempts[-1].outcome == "SUCCESS"
    assert {item.protocol for item in report.evidence} == {"HTTPS"}
    assert report.attempts[-1].protocol == "HTTPS"


@pytest.mark.parametrize(
    ("status", "failure", "outcome"),
    [
        (401, "AUTH_REJECTED", "FAILED"),
        (403, "AUTHORIZATION_DENIED", "FAILED"),
        (404, "ENDPOINT_UNSUPPORTED", "SKIPPED"),
        (405, "ENDPOINT_UNSUPPORTED", "SKIPPED"),
    ],
)
def test_http_failures_are_classified_without_retaining_response_body(status, failure, outcome) -> None:
    def handler(request):
        headers = {"WWW-Authenticate": _DIGEST_CHALLENGE} if status == 401 else {}
        return _response(request, status, b"password=sensitive-camera-body", headers)

    adapter, _sent = _adapter(handler)
    report = adapter.collect_report(_target())

    assert report.attempts[-1].error_category == failure
    assert report.attempts[-1].outcome is outcome
    assert "sensitive-camera-body" not in repr(report)
    assert "safe-pass" not in repr(report)


def test_final_digest_rejection_is_one_logical_attempt_and_does_not_store_challenge() -> None:
    def handler(request):
        return _response(
            request,
            401,
            b"denied",
            {"WWW-Authenticate": _DIGEST_CHALLENGE},
        )

    adapter, sent = _adapter(handler)
    report = adapter.collect_report(_target())

    assert len(sent) == 2
    assert len(report.attempts) == 1
    assert any(item.error_category in {"AUTH_REJECTED", "AUTHORIZATION_DENIED"} for item in report.attempts)
    assert _DIGEST_CHALLENGE not in repr(report)


@pytest.mark.parametrize(
    "unsupported",
    [
        'Digest realm="camera", nonce="abc123", qop="auth-int", algorithm=MD5',
        'Digest realm="camera", nonce="abc123", qop="auth", algorithm=SHA-256',
    ],
)
def test_unsupported_digest_challenge_is_distinct_from_credential_rejection(
    unsupported: str,
) -> None:
    adapter, sent = _adapter(
        lambda request: _response(
            request,
            401,
            headers={"WWW-Authenticate": unsupported},
        )
    )

    report = adapter.collect_report(_target())

    assert len(sent) == 1
    assert report.attempts[-1].error_category == "AUTH_MECHANISM_UNSUPPORTED"
    assert not any(item.error_category in {"AUTH_REJECTED", "AUTHORIZATION_DENIED"} for item in report.attempts)
    assert unsupported not in repr(report)


def test_forbidden_response_does_not_trigger_digest_retry_even_with_challenge() -> None:
    adapter, sent = _adapter(
        lambda request: _response(
            request,
            403,
            headers={"WWW-Authenticate": _DIGEST_CHALLENGE},
        )
    )

    report = adapter.collect_report(_target())

    assert len(sent) == 1
    assert report.attempts[-1].error_category == "AUTHORIZATION_DENIED"
    assert any(item.error_category in {"AUTH_REJECTED", "AUTHORIZATION_DENIED"} for item in report.attempts)


def test_each_camera_uses_only_its_own_digest_credential() -> None:
    authenticated_users: list[str] = []

    def handler(request):
        authorization = request.headers.get("Authorization")
        if authorization is None:
            return _response(
                request,
                401,
                headers={"WWW-Authenticate": _DIGEST_CHALLENGE},
            )
        authenticated_users.append(authorization.split('username="', maxsplit=1)[1].split('"', maxsplit=1)[0])
        return _response(request, 200, _DEVICE_INFO)

    adapter, sent = _adapter(handler)
    adapter.collect(_target("192.0.2.11", "first-user", "first-secret"))
    adapter.collect(_target("192.0.2.12", "second-user", "second-secret"))

    assert authenticated_users == ["first-user", "second-user"]
    assert all("first-secret" not in request.url and "second-secret" not in request.url for request in sent)


def test_redirect_is_not_followed_and_never_reaches_another_origin() -> None:
    adapter, sent = _adapter(
        lambda request: _response(
            request,
            302,
            headers={"Location": "http://example.invalid/"},
        )
    )

    report = adapter.collect_report(_target())

    assert len(sent) == 1
    assert urlsplit(sent[0].url).hostname == "192.0.2.10"
    assert report.attempts[-1].error_category == "INVALID_RESPONSE"


def test_read_timeout_is_normalized_without_retaining_exception_text() -> None:
    class TimeoutAdapter(BaseAdapter):
        def send(self, _request, **_kwargs):
            raise requests.ReadTimeout("safe-pass leaked by device")

        def close(self) -> None:
            return None

    def session_factory() -> requests.Session:
        session = requests.Session()
        session.mount("https://", TimeoutAdapter())
        return session

    report = HikvisionAdapter(session_factory=session_factory).collect_report(_target())

    assert report.attempts[-1].error_category == "READ_TIMEOUT"
    assert "safe-pass" not in repr(report)
    assert report.to_camera_result("192.0.2.10").error_message == "A consulta excedeu o tempo limite."


@pytest.mark.parametrize(
    "body",
    [
        b"<html>not XML</html>",
        b"<!DOCTYPE DeviceInfo [<!ENTITY x SYSTEM 'file:///secret'>]><DeviceInfo><manufacturer>&x;</manufacturer></DeviceInfo>",
        b"<DeviceInfo><manufacturer>" + b"x" * (64 * 1024) + b"</manufacturer></DeviceInfo>",
    ],
    ids=["html", "dtd", "oversized"],
)
def test_xml_parser_rejects_non_device_xml_dtd_and_oversized_content(body: bytes) -> None:
    adapter, _sent = _adapter(lambda request: _response(request, 200, body))

    report = adapter.collect_report(_target())

    assert not report.evidence
    assert report.attempts[-1].error_category == "INVALID_RESPONSE"


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16le", "utf-16be"])
def test_xml_parser_rejects_dtd_before_entity_expansion_in_supported_encodings(
    encoding: str,
) -> None:
    document = (
        "<?xml version='1.0' encoding='UTF-8'?>"
        "<!DOCTYPE DeviceInfo [<!ENTITY x SYSTEM 'file:///private/data'>]>"
        "<DeviceInfo><manufacturer>&x;</manufacturer></DeviceInfo>"
    )
    if encoding == "utf-8":
        body = document.encode("utf-8")
    else:
        declaration = document.replace("UTF-8", "UTF-16")
        marker = b"\xff\xfe" if encoding == "utf-16le" else b"\xfe\xff"
        body = marker + declaration.encode(encoding)

    with pytest.raises(ValueError):
        _parse_device_info(body)


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16le", "utf-16be"])
def test_xml_parser_preserves_valid_xml_in_supported_encodings(encoding: str) -> None:
    document = "<?xml version='1.0' encoding='UTF-8'?><DeviceInfo><model>DS 東京</model></DeviceInfo>"
    if encoding == "utf-8":
        body = document.encode("utf-8")
    else:
        declaration = document.replace("UTF-8", "UTF-16")
        marker = b"\xff\xfe" if encoding == "utf-16le" else b"\xfe\xff"
        body = marker + declaration.encode(encoding)

    assert _parse_device_info(body) == {"model": "DS 東京"}


def test_target_credentials_are_not_kept_when_echoed_in_device_fields() -> None:
    secret = "sensitive-password-987"
    body = (
        b"<DeviceInfo><manufacturer>"
        + secret.encode()
        + b"</manufacturer><model>Camera</model></DeviceInfo>"
    )
    adapter, _sent = _adapter(lambda request: _response(request, 200, body))

    report = adapter.collect_report(_target(password=secret))

    assert all(secret not in record.value for record in report.evidence)
    assert secret not in repr(report)
    assert secret not in repr(report.to_camera_result("192.0.2.10"))


def test_ipv6_target_and_transport_settings_are_explicit_and_bounded() -> None:
    call_options: dict[str, object] = {}
    sent: list[requests.PreparedRequest] = []

    class InstrumentedSession(requests.Session):
        def get(self, url, **kwargs):
            call_options.update(kwargs)
            return super().get(url, **kwargs)

    class OfflineAdapter(BaseAdapter):
        def send(self, request, **_kwargs):
            sent.append(request)
            response = _response(request, 200, _DEVICE_INFO)
            response.connection = self
            return response

        def close(self) -> None:
            return None

    def session_factory() -> requests.Session:
        session = InstrumentedSession()
        session.mount("https://", OfflineAdapter())
        return session

    HikvisionAdapter(session_factory=session_factory).collect(_target("2001:db8::10"))

    assert urlsplit(sent[0].url).hostname == "2001:db8::10"
    assert call_options["allow_redirects"] is False
    assert call_options["timeout"] == (3.0, 7.0)
    assert call_options["verify"] is True
    assert call_options["stream"] is True
    assert call_options["auth"].__class__.__name__ == "_BoundedDigestAuth"
    assert sent[0].url.startswith("https://")


def test_tls_failure_is_reported_without_http_downgrade() -> None:
    class TLSFailureAdapter(BaseAdapter):
        def send(self, _request, **_kwargs):
            raise requests.exceptions.SSLError("untrusted certificate")

        def close(self) -> None:
            return None

    requests_seen: list[requests.PreparedRequest] = []

    class RecordingTLSFailureAdapter(TLSFailureAdapter):
        def send(self, request, **kwargs):
            requests_seen.append(request)
            return super().send(request, **kwargs)

    def session_factory() -> requests.Session:
        session = requests.Session()
        session.mount("https://", RecordingTLSFailureAdapter())
        return session

    report = HikvisionAdapter(session_factory=session_factory).collect_report(_target())

    assert len(requests_seen) == 1
    assert requests_seen[0].url.startswith("https://")
    assert report.attempts[-1].error_category == "TLS_ERROR"
    assert report.attempts[-1].protocol == "HTTPS"


class _Discoverer:
    def discover(self, _target: CameraTarget) -> PreAuthEvidence:
        return PreAuthEvidence(capabilities={"Manufacturer": "Hikvision"})


class _OnvifCollector:
    def __init__(self) -> None:
        self.calls = 0

    def collect(self, target: CameraTarget) -> CameraResult:
        self.calls += 1
        return CameraResult(
            ip=target.ip,
            status=CollectionStatus.SUCCESS,
            manufacturer="Hikvision",
            model="Model A",
            serial="serial-onvif",
            firmware="1.0",
            collection_method=CollectionMethod.ONVIF,
        )


def test_unsupported_isapi_falls_back_to_onvif_and_records_both_attempts() -> None:
    adapter, _sent = _adapter(lambda request: _response(request, 404))
    registry = AdapterRegistry()
    registry.register("Hikvision", adapter)
    onvif = _OnvifCollector()
    collector = VendorFirstCollector(registry=registry, discoverer=_Discoverer(), onvif_collector=onvif)

    report = collector.collect_report(_target())
    result = report.to_camera_result("192.0.2.10")

    assert onvif.calls == 1
    assert result.status is CollectionStatus.SUCCESS
    assert result.collection_method is CollectionMethod.ONVIF
    assert len(report.attempts) == 2


def test_auth_rejection_stops_before_onvif_fallback() -> None:
    adapter, _sent = _adapter(
        lambda request: _response(
            request,
            401,
            headers={"WWW-Authenticate": _DIGEST_CHALLENGE},
        )
    )
    registry = AdapterRegistry()
    registry.register("Hikvision", adapter)
    onvif = _OnvifCollector()
    collector = VendorFirstCollector(registry=registry, discoverer=_Discoverer(), onvif_collector=onvif)

    result = collector.collect(_target())

    assert onvif.calls == 0
    assert result.status is CollectionStatus.PARTIAL_SUCCESS
    assert result.error_code is not None
    assert result.manufacturer == "Hikvision"


def test_isapi_evidence_survives_later_onvif_auth_failure() -> None:
    partial_xml = b"<DeviceInfo><manufacturer>Hikvision</manufacturer><model>Model A</model></DeviceInfo>"
    adapter, _sent = _adapter(lambda request: _response(request, 200, partial_xml))
    registry = AdapterRegistry()
    registry.register("Hikvision", adapter)

    class RejectingOnvif:
        def collect(self, _target: CameraTarget) -> CameraResult:
            from zeep.exceptions import Fault

            raise Fault("NotAuthorized")

    collector = VendorFirstCollector(
        registry=registry,
        discoverer=_Discoverer(),
        onvif_collector=RejectingOnvif(),
    )

    report = collector.collect_report(_target())
    result = report.to_camera_result("192.0.2.10")

    assert result.status is CollectionStatus.PARTIAL_SUCCESS
    assert result.manufacturer == "Hikvision"
    assert result.model == "Model A"
    assert result.error_code is not None
    assert any(item.source == "VENDOR" for item in report.evidence)
    assert len(report.attempts) == 2
