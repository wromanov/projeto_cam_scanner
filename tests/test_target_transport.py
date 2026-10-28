"""Offline checks for the target-bound Requests/Zeep path."""
from __future__ import annotations

import ssl
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar
from urllib.parse import urlsplit

import pytest
import requests
from requests.adapters import HTTPAdapter
from zeep.exceptions import Fault

from cam_scanner.application.collection_context import (
    CollectionCancelled,
    CollectionContext,
    CollectionTLSFailure,
)
from cam_scanner.cameras.transport import (
    ControlledOnvifClient,
    ResponseTooLarge,
    TargetRejected,
    TargetTransportPolicy,
    _BoundedResponse,
    _RestrictedService,
)
from cam_scanner.config.models import EffectiveConfig, TransportProfile
from cam_scanner.config.transport_plan import select_transport
from cam_scanner.domain.models import CameraTarget


def _context(
    port: int | None = None,
    *,
    component: str = "onvif_device",
    protocol: str = "https",
    clock: Callable[[], float] | None = None,
) -> CollectionContext:
    rules = () if port is None else (SimpleNamespace(
        target="127.0.0.1", component=component, protocol=protocol, host=None,
        port=port,
    ),)
    options = {"transport_factory": TargetTransportPolicy}
    if clock is not None:
        options["clock"] = clock
    return CollectionContext(
        CameraTarget("127.0.0.1", "operator", "secret"),
        SimpleNamespace(transport_rules=rules),
        **options,
    )


class _HttpsServer:
    def __init__(self, handler: type[BaseHTTPRequestHandler]) -> None:
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(
            Path(__file__).with_name("tls_test_server_cardb.pem"),
            Path(__file__).with_name("tls_test_server_cardb.key"),
        )
        self.httpd.socket = tls.wrap_socket(self.httpd.socket, server_side=True)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def server_port(self) -> int:
        return self.httpd.server_port

    def start(self) -> None:
        self.thread.start()

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)


def _trust_test_ca_for_ports(monkeypatch: pytest.MonkeyPatch, ports: set[int]) -> None:
    original_send = HTTPAdapter.send
    ca_bundle = str(Path(__file__).with_name("tls_test_ca_cardb.pem"))

    def send(adapter, request, **kwargs):
        parsed = urlsplit(request.url)
        if parsed.scheme == "https" and parsed.hostname == "127.0.0.1" and parsed.port in ports:
            assert kwargs.get("verify") is True
            kwargs["verify"] = ca_bundle
        return original_send(adapter, request, **kwargs)

    monkeypatch.setattr(HTTPAdapter, "send", send)


def _one_retry_context(component: str = "vendor_axis") -> CollectionContext:
    context = _context(component=component)
    context.config.max_retries = 1
    context.config.retry_backoff_seconds = 0.01
    context.wait_for_retry = lambda *_args: True  # type: ignore[method-assign]
    return context


def test_transport_rejects_cross_target_credentials_and_unapproved_http() -> None:
    context = _context()
    try:
        assert context.transport.authorize(
            "onvif_device", "https://127.0.0.1:443/onvif/device_service"
        )
        for url in (
            "http://127.0.0.1:80/onvif/device_service",
            "https://127.0.0.2:443/onvif/device_service",
            "https://operator:secret@127.0.0.1/onvif/device_service",
            "https://127.0.0.1/onvif/device_service#fragment",
            "https://example.com/onvif/device_service",
        ):
            with pytest.raises(TargetRejected):
                context.transport.authorize("onvif_device", url)
    finally:
        context.close()


def test_real_zeep_uses_local_wsdl_and_guarded_requests_before_soap_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[tuple[str, bytes]] = []
    soap = (b'<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" '
            b'xmlns:tds="http://www.onvif.org/ver10/device/wsdl">'
            b'<s:Body><tds:GetDeviceInformationResponse>'
            b'<tds:Manufacturer>Axis</tds:Manufacturer><tds:Model>M1</tds:Model>'
            b'<tds:FirmwareVersion>1.0</tds:FirmwareVersion>'
            b'<tds:SerialNumber>S1</tds:SerialNumber>'
            b'<tds:HardwareId>H1</tds:HardwareId>'
            b'</tds:GetDeviceInformationResponse></s:Body></s:Envelope>')

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = self.rfile.read(int(self.headers["Content-Length"]))
            observed.append((self.path, body))
            self.send_response(200)
            self.send_header("Content-Type", "application/soap+xml")
            self.send_header("Content-Length", str(len(soap)))
            self.end_headers()
            self.wfile.write(soap)

        def log_message(self, *_args: object) -> None:
            pass

    server = _HttpsServer(Handler)
    server.start()
    _trust_test_ca_for_ports(monkeypatch, {server.server_port})
    context = _context(server.server_port)
    try:
        assert context.auth.begin("ONVIF", "primary")
        client = ControlledOnvifClient(context, authenticated=True)
        assert observed == []  # Construction and WSDL imports do not call the camera.
        response = client.devicemgmt().GetDeviceInformation()
        assert response.Manufacturer == "Axis"
        assert len(observed) == 1
        assert observed[0][0] == "/onvif/device_service"
        assert b"UsernameToken" in observed[0][1]
        assert context.auth.allows_authenticated_request("ONVIF")
        assert context.auth.physical_exchanges == 1
        session = context.transport._sessions[("onvif_device", "ONVIF", True)]
        assert session.trust_env is False
        assert session.proxies == {}
    finally:
        context.close()
        server.close()


def test_real_zeep_discovers_only_authorized_media_xaddr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = (b'<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" '
                    b'xmlns:tds="http://www.onvif.org/ver10/device/wsdl" '
                    b'xmlns:tt="http://www.onvif.org/ver10/schema"><s:Body>'
                    b'<tds:GetCapabilitiesResponse><tds:Capabilities>'
                    b'<tt:Media><tt:XAddr>https://127.0.0.1:'
                    + str(self.server.server_port).encode() + b'/onvif/media</tt:XAddr>'
                    b'</tt:Media></tds:Capabilities></tds:GetCapabilitiesResponse>'
                    b'</s:Body></s:Envelope>')
            self.send_response(200)
            self.send_header("Content-Type", "application/soap+xml")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args: object) -> None:
            pass

    server = _HttpsServer(Handler)
    server.start()
    _trust_test_ca_for_ports(monkeypatch, {server.server_port})
    context = _context(server.server_port)
    try:
        result = ControlledOnvifClient(context, authenticated=False).devicemgmt().GetCapabilities(
            Category="All"
        )
        assert result.Media.XAddr.endswith("/onvif/media")
        assert context.transport.media_address is None  # Media has no approved rule.
    finally:
        context.close()
        server.close()


def test_authenticated_adapter_requires_started_family_and_allows_digest_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context(component="vendor_hikvision")
    sent = 0

    def synthetic_send(adapter: HTTPAdapter, request: requests.PreparedRequest,
                       **_kwargs: object) -> requests.Response:
        nonlocal sent
        sent += 1
        response = requests.Response()
        response.request = request
        response.url = request.url
        response.connection = adapter
        response.raw = SimpleNamespace(close=lambda: None)
        if "Authorization" in request.headers:
            response.status_code = 200
            response._content = b"ok"
        else:
            response.status_code = 401
            response.headers["WWW-Authenticate"] = 'Digest realm="camera", nonce="n"'
            response._content = b"challenge"
        return response

    monkeypatch.setattr(HTTPAdapter, "send", synthetic_send)
    try:
        url = "https://127.0.0.1/cgi-bin/param.cgi"
        session = context.transport._session("vendor_hikvision", "NATIVE", True)
        prepared = session.prepare_request(requests.Request("GET", url))
        adapter = session.get_adapter(url)
        with pytest.raises(TargetRejected, match="authorized"):
            adapter.send(prepared, timeout=(1.0, 1.0), verify=True)
        assert context.auth.physical_exchanges == 0
        assert sent == 0

        assert context.auth.begin("VENDOR_HIKVISION", "primary")
        response = context.transport.request(
            "vendor_hikvision", "GET", url, source="NATIVE", authenticated=True,
            auth=requests.auth.HTTPDigestAuth("operator", "secret"),
        )
        assert response.status_code == 200
        assert sent == 2  # Initial challenge and authorized Digest replay.
        assert context.auth.physical_exchanges == 2
        assert context.auth.allows_authenticated_request("VENDOR_HIKVISION")

        second_response = context.transport.request(
            "vendor_hikvision", "GET", url, source="NATIVE", authenticated=True,
            auth=requests.auth.HTTPDigestAuth("operator", "secret"),
        )
        assert second_response.status_code == 200
        assert sent == 4  # A new operation may negotiate Digest on the same URL.
        assert context.auth.physical_exchanges == 4
        assert context.auth.allows_authenticated_request("VENDOR_HIKVISION")
    finally:
        context.close()


def test_real_digest_replay_does_not_follow_redirect_or_forward_authentication() -> None:
    source_requests: list[dict[str, str]] = []
    destination_requests: list[dict[str, str]] = []
    destination = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        type("Sink", (BaseHTTPRequestHandler,), {
            "do_GET": lambda self: (
                destination_requests.append(dict(self.headers.items())),
                self.send_response(200),
                self.send_header("Content-Length", "0"),
                self.end_headers(),
            ),
            "log_message": lambda self, *_args: None,
        }),
    )
    sink_thread = threading.Thread(target=destination.serve_forever, daemon=True)
    sink_thread.start()
    redirect_url = f"http://127.0.0.1:{destination.server_port}/capture"

    class DigestRedirectHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            source_requests.append(dict(self.headers.items()))
            if self.headers.get("Authorization") is None:
                self.send_response(401)
                self.send_header(
                    "WWW-Authenticate",
                    'Digest realm="offline-camera", nonce="nonce-1", qop="auth"',
                )
            else:
                self.send_response(307)
                self.send_header("Location", redirect_url)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *_args: object) -> None:
            pass

    source = ThreadingHTTPServer(("127.0.0.1", 0), DigestRedirectHandler)
    source_thread = threading.Thread(target=source.serve_forever, daemon=True)
    source_thread.start()
    target = CameraTarget("127.0.0.1", "operator", "secret")
    profile = TransportProfile(
        id="TEST_HTTP_DIGEST",
        targets=(target.ip,),
        component="vendor_hikvision",
        protocol="http",
        port=source.server_port,
        auth_mode="NATIVE_DIGEST_EXISTING",
        authorization_ref="AUTH-TEST",
        http_risk_accepted=True,
    )
    config = select_transport(
        EffectiveConfig(transport_profiles=(profile,)),
        (target,),
        {target.ip: "vendor_hikvision"},
        selection_id=profile.id,
    )
    context = CollectionContext(target, config, transport_factory=TargetTransportPolicy)
    try:
        assert context.auth.begin("VENDOR_HIKVISION", "primary")
        response = context.transport.request(
            "vendor_hikvision",
            "GET",
            f"http://127.0.0.1:{source.server_port}/digest",
            source="NATIVE",
            authenticated=True,
            auth=requests.auth.HTTPDigestAuth("operator", "secret"),
        )
        try:
            assert response.status_code == 307
        finally:
            response.close()

        assert len(source_requests) == 2
        assert "Authorization" not in source_requests[0]
        assert source_requests[1].get("Authorization", "").startswith("Digest ")
        assert "Proxy-Authorization" not in source_requests[1]
        assert destination_requests == []
        assert context.auth.physical_exchanges == 2
    finally:
        context.close()
        source.shutdown()
        source.server_close()
        source_thread.join(timeout=2)
        destination.shutdown()
        destination.server_close()
        sink_thread.join(timeout=2)


def test_anonymous_system_date_time_soap_fault_keeps_authentication_unknown() -> None:
    context = _context()

    class NotAuthorized(Exception):
        code = "ter:NotAuthorized"

    class DeviceService:
        _binding_options: ClassVar[dict[str, object]] = {}

        def GetSystemDateAndTime(self) -> None:
            raise NotAuthorized("synthetic anonymous fault")

    service = _RestrictedService(
        DeviceService(), "onvif_device", context, authenticated=False
    )
    try:
        with pytest.raises(NotAuthorized):
            service.GetSystemDateAndTime()
        assert context.auth.state == context.auth.AUTH_SCOPE_UNKNOWN
        assert not context.auth.begin(
            "VENDOR:AXIS", "MISSING_IDENTITY", missing_identity_fields=("serial",)
        )
        assert context.auth.begin("ONVIF", "PRIMARY")
        assert context.auth.allows_authenticated_attempt("ONVIF")
        assert not context.auth.begin(
            "VENDOR:AXIS", "MISSING_IDENTITY", missing_identity_fields=("serial",)
        )
    finally:
        context.close()


def test_authenticated_not_authorized_fault_keeps_ambiguous_state_and_blocks_scope() -> None:
    context = _context()

    class DeviceService:
        _binding_options: ClassVar[dict[str, object]] = {}

        def GetSystemDateAndTime(self) -> None:
            raise Fault("NotAuthorized")

    assert context.auth.begin("ONVIF", "PRIMARY")
    context.auth.observe_http(200, "ONVIF", authenticated=True)
    service = _RestrictedService(
        DeviceService(), "onvif_device", context, authenticated=True
    )
    try:
        with pytest.raises(Fault):
            service.GetSystemDateAndTime()
        assert context.auth.state == context.auth.AUTH_ACCEPTED
        assert context.auth.soap_access_blocked
        assert not context.auth.allows_authenticated_request("ONVIF")
        assert not context.auth.begin("ONVIF", "PRIMARY")
    finally:
        context.close()


def test_onvif_wsse_401_with_digest_header_is_final_not_http_digest_challenge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context()
    sent = 0

    def synthetic_send(_adapter: HTTPAdapter, request: requests.PreparedRequest,
                       **_kwargs: object) -> requests.Response:
        nonlocal sent
        sent += 1
        response = requests.Response()
        response.status_code = 401
        response.headers["WWW-Authenticate"] = 'Digest realm="camera", nonce="n"'
        response._content = b""
        response.request = request
        response.url = request.url
        return response

    monkeypatch.setattr(HTTPAdapter, "send", synthetic_send)
    try:
        assert context.auth.begin("ONVIF", "primary")
        response = context.transport.request(
            "onvif_device", "POST",
            "https://127.0.0.1/onvif/device_service", source="ONVIF",
            authenticated=True, data=b"<soap/>",
        )
        assert response.status_code == 401
        assert context.auth.state == context.auth.AUTH_REJECTED_FINAL
        assert sent == 1
        assert context.auth.physical_exchanges == 1
    finally:
        context.close()


def test_digest_challenge_body_is_bounded_before_auth_hook_and_exchange_is_counted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context(component="vendor_hikvision")
    sent = 0
    bytes_read = 0

    def synthetic_send(_adapter: HTTPAdapter, request: requests.PreparedRequest,
                       **_kwargs: object) -> requests.Response:
        nonlocal sent
        sent += 1
        response = requests.Response()
        response.request = request
        response.url = request.url
        response.raw = SimpleNamespace(close=lambda: None)
        if "Authorization" in request.headers:
            response.status_code = 401
            response.headers["Content-Length"] = "2"
            response._content = b"no"
        else:
            response.status_code = 401
            response.headers["WWW-Authenticate"] = 'Digest realm="camera", nonce="n"'
            response.headers["Content-Length"] = str(2 * 1024 * 1024)
            response.connection = _adapter

            def chunks(chunk_size: int = 65536, **_options: object):
                nonlocal bytes_read
                for _ in range(40):
                    chunk = b"x" * chunk_size
                    bytes_read += len(chunk)
                    yield chunk

            response.iter_content = chunks  # type: ignore[method-assign]
        return response

    monkeypatch.setattr(HTTPAdapter, "send", synthetic_send)
    try:
        assert context.auth.begin("VENDOR_HIKVISION", "primary")
        with pytest.raises(ResponseTooLarge, match="challenge body too large"):
            context.transport.request(
                "vendor_hikvision", "GET", "https://127.0.0.1/ISAPI/System/deviceInfo",
                source="NATIVE", authenticated=True,
                auth=requests.auth.HTTPDigestAuth("operator", "secret"),
            )
        assert bytes_read <= 1024 * 1024 + 65536
        assert bytes_read == 0  # Rejected by Content-Length before Requests' Digest hook.
        assert context.auth.physical_exchanges == 1
        assert sent == 1
        assert context.auth.state == context.auth.AUTH_REJECTED_FINAL
        assert not context.auth.begin("ONVIF", "primary")
    finally:
        context.close()


@pytest.mark.parametrize(
    ("challenge", "replay_blocked"),
    [
        ('Basic realm="camera"', False),
        ('Digest realm="camera", nonce="n", algorithm="UNKNOWN"', True),
        ('Digest realm="camera", nonce="n", qop="auth", algorithm="SHA-256"', True),
    ],
)
def test_unsupported_401_challenge_closes_auth_scope_without_network_replay(
    monkeypatch: pytest.MonkeyPatch,
    challenge: str,
    replay_blocked: bool,
) -> None:
    context = _context(component="vendor_hikvision")
    sent = 0

    def synthetic_send(adapter: HTTPAdapter, request: requests.PreparedRequest,
                       **_kwargs: object) -> requests.Response:
        nonlocal sent
        sent += 1
        response = requests.Response()
        response.status_code = 401
        response.headers["WWW-Authenticate"] = challenge
        response._content = b"denied"
        response._content_consumed = True
        response.request = request
        response.url = request.url
        response.connection = adapter
        response.raw = SimpleNamespace(close=lambda: None)
        return response

    monkeypatch.setattr(HTTPAdapter, "send", synthetic_send)
    try:
        assert context.auth.begin("VENDOR_HIKVISION", "primary")
        def operation() -> requests.Response:
            return context.transport.request(
                "vendor_hikvision", "GET", "https://127.0.0.1/ISAPI/System/deviceInfo",
                source="NATIVE", authenticated=True,
                auth=requests.auth.HTTPDigestAuth("operator", "secret"),
            )
        if replay_blocked:
            with pytest.raises(TargetRejected, match="authenticated attempt"):
                operation()
        else:
            assert operation().status_code == 401
        assert sent == 1
        assert context.auth.physical_exchanges == 1
        assert context.auth.state == context.auth.AUTH_REJECTED_FINAL
        assert not context.auth.begin("ONVIF", "primary")
    finally:
        context.close()


def test_stream_chunk_read_time_is_charged_before_next_budget_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = [0.0]

    def clock() -> float:
        return now[0]

    context = _context(clock=clock)

    class SyntheticResponse:
        def __init__(self) -> None:
            self.headers: dict[str, str] = {}

        def iter_content(self, **_options: object):
            now[0] += 2.0  # Time spent receiving the first body chunk.
            yield b"chunk"

        def close(self) -> None:
            pass

    observed_remaining: list[float] = []
    original_check = context.check

    def checkpoint(source: str) -> float:
        observed_remaining.append(context.budget.remaining(source))
        return original_check(source)

    context.check = checkpoint  # type: ignore[method-assign]
    bounded = _BoundedResponse(SyntheticResponse(), context, "ONVIF", 1024)  # type: ignore[arg-type]
    try:
        assert list(bounded.iter_content()) == [b"chunk"]
        assert observed_remaining
        assert observed_remaining[0] == pytest.approx(13.0)
    finally:
        context.close()


def test_cancellation_during_stream_chunks_closes_response_at_next_checkpoint() -> None:
    cancel_event = threading.Event()
    context = CollectionContext(
        CameraTarget("127.0.0.1", "operator", "secret"),
        SimpleNamespace(),
        cancel_event=cancel_event,
    )
    response = requests.Response()
    response.headers["Content-Length"] = "11"
    close_calls: list[bool] = []
    response.close = lambda: close_calls.append(True)  # type: ignore[method-assign]

    def chunks(**_options: object):
        yield b"first"
        cancel_event.set()
        yield b"second"

    response.iter_content = chunks  # type: ignore[method-assign]
    bounded = _BoundedResponse(response, context, "NATIVE", 1024)
    try:
        with pytest.raises(CollectionCancelled):
            list(bounded.iter_content())
        assert cancel_event.is_set()
        assert close_calls == [True]
        assert bounded._cached is None
    finally:
        context.close()


def test_idempotent_get_body_timeout_uses_one_configured_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _one_retry_context()
    sent = 0

    def synthetic_send(_adapter: HTTPAdapter, request: requests.PreparedRequest,
                       **_kwargs: object) -> requests.Response:
        nonlocal sent
        sent += 1
        response = requests.Response()
        response.status_code = 200
        response.request = request
        response.url = request.url
        if sent == 1:
            response.raw = SimpleNamespace(close=lambda: None)

            def timeout_chunks(**_options: object):
                raise requests.exceptions.ReadTimeout("synthetic body timeout")

            response.iter_content = timeout_chunks  # type: ignore[method-assign]
        else:
            response._content = b"ok"
            response._content_consumed = True
        return response

    monkeypatch.setattr(HTTPAdapter, "send", synthetic_send)
    try:
        response = context.transport.request(
            "vendor_axis", "GET", "https://127.0.0.1/cgi-bin/param.cgi",
            source="NATIVE", authenticated=False,
        )
        assert list(response.iter_content()) == [b"ok"]
        assert sent == 2
        assert context.auth.physical_exchanges == 2
    finally:
        context.close()


def test_tls_auth_failure_and_nonretryable_soap_are_not_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _one_retry_context()
    tls_context = _one_retry_context()
    sent = 0

    def synthetic_send(_adapter: HTTPAdapter, request: requests.PreparedRequest,
                       **_kwargs: object) -> requests.Response:
        nonlocal sent
        sent += 1
        if request.url.endswith("/tls-error"):
            raise requests.exceptions.SSLError("synthetic certificate failure")
        response = requests.Response()
        response.request = request
        response.url = request.url
        response.raw = SimpleNamespace(close=lambda: None)
        if request.url.endswith("/auth-rejected"):
            response.status_code = 401
            response._content = b"denied"
            response._content_consumed = True
        else:
            response.status_code = 503
            response._content = b"unavailable"
            response._content_consumed = True
        return response

    monkeypatch.setattr(HTTPAdapter, "send", synthetic_send)
    try:
        with pytest.raises(requests.exceptions.SSLError):
            tls_context.transport.request(
                "vendor_axis", "GET", "https://127.0.0.1/tls-error",
                source="NATIVE", authenticated=False,
            )
        assert sent == 1
        assert tls_context.tls_failed
        with pytest.raises(CollectionTLSFailure):
            tls_context.transport.request(
                "vendor_axis", "GET", "https://127.0.0.1/blocked-after-tls",
                source="NATIVE", authenticated=False,
            )
        assert sent == 1

        rejected = context.transport.request(
            "vendor_axis", "GET", "https://127.0.0.1/auth-rejected",
            source="NATIVE", authenticated=False,
        )
        assert rejected.status_code == 401
        assert sent == 2

        assert context.auth.begin("ONVIF", "primary")
        soap = (b'<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" '
                b'xmlns:tds="http://www.onvif.org/ver10/device/wsdl">'
                b'<s:Body><tds:GetCapabilities/></s:Body></s:Envelope>')
        unavailable = context.transport.request(
            "onvif_device", "POST", "https://127.0.0.1/onvif/device_service",
            source="ONVIF", authenticated=True, data=soap,
        )
        assert unavailable.status_code == 503
        assert sent == 3
        assert context.auth.physical_exchanges == 2
    finally:
        context.close()
        tls_context.close()


def test_tls_failure_while_streaming_closes_context_and_blocks_next_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _one_retry_context()
    sent = 0
    closed = 0

    def synthetic_send(_adapter: HTTPAdapter, request: requests.PreparedRequest,
                       **_kwargs: object) -> requests.Response:
        nonlocal sent, closed
        sent += 1
        response = requests.Response()
        response.status_code = 200
        response.request = request
        response.url = request.url

        def close() -> None:
            nonlocal closed
            closed += 1

        response.raw = SimpleNamespace(close=close)

        def tls_failure(**_options: object):
            raise requests.exceptions.SSLError("synthetic body certificate failure")

        response.iter_content = tls_failure  # type: ignore[method-assign]
        return response

    monkeypatch.setattr(HTTPAdapter, "send", synthetic_send)
    try:
        with pytest.raises(requests.exceptions.SSLError):
            context.transport.request(
                "vendor_axis", "GET", "https://127.0.0.1/body-tls-error",
                source="NATIVE", authenticated=False,
            )
        assert context.tls_failed
        assert sent == 1
        assert closed == 1
        with pytest.raises(CollectionTLSFailure):
            context.transport.request(
                "vendor_axis", "GET", "https://127.0.0.1/blocked-after-body-tls",
                source="NATIVE", authenticated=False,
            )
        assert sent == 1
    finally:
        context.close()
