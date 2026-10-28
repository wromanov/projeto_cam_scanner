"""Cross-invariant coverage from real SINGLE collection into the disabled RTSP guard.

The only network endpoint is a synthetic loopback HTTPS server. Production
workflow, inventory, collector, registry, adapters, transport and snapshot
service stay in the path; only the two HTTP snapshot providers are inert stubs.
"""
from __future__ import annotations

import ssl
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Self
from urllib.parse import urlsplit

import pytest
from requests.adapters import HTTPAdapter

from cam_scanner.application.inventory_service import InventoryService
from cam_scanner.application.single_workflow import SingleWorkflow
from cam_scanner.cameras.registry import build_default_registry
from cam_scanner.cameras.strategy import VendorFirstCollector
from cam_scanner.config.models import EffectiveConfig, TransportRule
from cam_scanner.domain.enums import MainMenuChoice
from cam_scanner.domain.models import CameraTarget
from cam_scanner.snapshot.rtsp import RtspFrameProvider
from cam_scanner.snapshot.service import (
    SnapshotCaptureError,
    SnapshotFailure,
    SnapshotMethod,
    SnapshotResult,
    SnapshotService,
)

_USERNAME = "cross-invariant-user-sentinel"
_PASSWORD = "cross-invariant-password-sentinel"
_MODEL = "WV-S2531L"
_DEVICE_INFO = (
    b'<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" '
    b'xmlns:tds="http://www.onvif.org/ver10/device/wsdl"><s:Body>'
    b'<tds:GetDeviceInformationResponse><tds:Manufacturer>Panasonic</tds:Manufacturer>'
    b'<tds:Model>WV-S2531L</tds:Model><tds:FirmwareVersion>fixture-fw</tds:FirmwareVersion>'
    b'<tds:SerialNumber>fixture-serial</tds:SerialNumber><tds:HardwareId>fixture-hw</tds:HardwareId>'
    b'</tds:GetDeviceInformationResponse></s:Body></s:Envelope>'
)


class _HttpsFixture:
    def __init__(self) -> None:
        self.requests: list[tuple[str, str, str | None]] = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                owner.requests.append(("GET", self.path, self.headers.get("Authorization")))
                if self.path == "/cgi-bin/getinfo?FILE=1":
                    # Valid but incomplete Panasonic evidence causes the real collector
                    # to continue to authenticated ONVIF for the remaining identity.
                    body = b"NAME=WV-S2531L\nSERIAL=fixture-serial\n"
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def do_POST(self) -> None:
                body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                operation = "GetDeviceInformation" if b"GetDeviceInformation" in body else "other"
                owner.requests.append(("POST", self.path, operation))
                self.send_response(200)
                self.send_header("Content-Type", "application/soap+xml; charset=utf-8")
                self.send_header("Content-Length", str(len(_DEVICE_INFO)))
                self.end_headers()
                self.wfile.write(_DEVICE_INFO)

            def log_message(self, *_args: object) -> None:
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(
            Path(__file__).with_name("tls_test_server_cardb.pem"),
            Path(__file__).with_name("tls_test_server_cardb.key"),
        )
        self.httpd.socket = tls.wrap_socket(self.httpd.socket, server_side=True)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def port(self) -> int:
        return self.httpd.server_port

    def __enter__(self) -> Self:
        self.thread.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)


def _trust_fixture_ca(monkeypatch: pytest.MonkeyPatch, port: int) -> None:
    original_send = HTTPAdapter.send
    ca = str(Path(__file__).with_name("tls_test_ca_cardb.pem"))

    def send(adapter, request, **kwargs):
        parsed = urlsplit(request.url)
        if parsed.scheme == "https" and parsed.hostname == "127.0.0.1" and parsed.port == port:
            assert kwargs.get("verify") is True
            kwargs["verify"] = ca
        return original_send(adapter, request, **kwargs)

    monkeypatch.setattr(HTTPAdapter, "send", send)


class _SingleUI:
    def __init__(self) -> None:
        self.report = None
        self.snapshot = None
        self.rendered_text = ""

    def prompt_camera_target(self) -> CameraTarget:
        return CameraTarget("127.0.0.1", _USERNAME, _PASSWORD)

    def prompt_manufacturer_hint(self) -> str:
        return "Panasonic"

    def prompt_model_hint(self) -> str:
        return _MODEL

    def prompt_transport_selection(self, _options) -> str:
        return "HTTPS_DEFAULT"

    def render_report(self, report, **kwargs: object) -> None:
        self.report = report
        self.snapshot = kwargs["snapshot"]
        self.rendered_text = repr((report, self.snapshot))

    def post_query_menu(self) -> MainMenuChoice:
        return MainMenuChoice.EXIT


class _HttpSnapshotStub:
    def __init__(self, calls: list[str], name: str) -> None:
        self.calls = calls
        self.name = name

    def capture(self, _target: CameraTarget, **_kwargs: object) -> bytes:
        self.calls.append(self.name)
        raise SnapshotCaptureError(SnapshotFailure.UNSUPPORTED)


def test_single_real_collection_reaches_disabled_rtsp_guard_without_media_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from cam_scanner.snapshot import rtsp as rtsp_module

    media_tripwires: list[str] = []

    class ForbiddenLock:
        def acquire(self, *_args: object, **_kwargs: object) -> bool:
            media_tripwires.append("lock")
            raise AssertionError("disabled RTSP must stop before acquiring the media lock")

        def release(self) -> None:
            media_tripwires.append("release")

    class ForbiddenAv:
        def open(self, *_args: object, **_kwargs: object) -> object:
            media_tripwires.append("pyav.open")
            raise AssertionError("disabled RTSP must not open PyAV")

    def forbidden_client(**_kwargs: object) -> object:
        media_tripwires.append("onvif.media_client")
        raise AssertionError("disabled RTSP must stop before media ONVIF")

    monkeypatch.setattr(rtsp_module, "_RTSP_CAPTURE_ENABLED", False)
    monkeypatch.setattr(rtsp_module, "_RTSP_CAPTURE_LOCK", ForbiddenLock())
    http_snapshot_calls: list[str] = []
    snapshot_service = SnapshotService(
        _HttpSnapshotStub(http_snapshot_calls, "onvif_http"),
        _HttpSnapshotStub(http_snapshot_calls, "vendor_http"),
        RtspFrameProvider(client_factory=forbidden_client, av_module=ForbiddenAv()),
    )

    with _HttpsFixture() as fixture:
        _trust_fixture_ca(monkeypatch, fixture.port)
        config = EffectiveConfig(
            request_timeout_seconds=3.0,
            camera_soft_deadline_seconds=20.0,
            transport_rules=tuple(
                TransportRule("127.0.0.1", component, "https", None, fixture.port)
                for component in ("vendor_panasonic", "onvif_device")
            ),
        )
        inventory = InventoryService(
            VendorFirstCollector(registry=build_default_registry()), config=config,
        )
        ui = _SingleUI()
        assert SingleWorkflow(ui, inventory, snapshot_service).run() is MainMenuChoice.EXIT

    report = ui.report
    snapshot = ui.snapshot
    assert report is not None and isinstance(snapshot, SnapshotResult)
    result = report.to_camera_result("127.0.0.1")
    assert result.model == _MODEL, [
        (attempt.operation, attempt.outcome, attempt.http_status, attempt.error_category)
        for attempt in report.attempts
        ] + [("fixture", request) for request in fixture.requests]
    assert report.model_hint is not None and report.model_hint.match_key == "wv-s2531l"
    assert any(
        attempt.operation == "GET /cgi-bin/getinfo"
        and attempt.http_status == 200
        and attempt.error_category is None
        for attempt in report.attempts
    )
    assert any(
        attempt.operation == "GetDeviceInformation"
        and attempt.outcome == "SUCCESS"
        for attempt in report.attempts
    )
    assert [method for method, _, _ in fixture.requests] == ["GET", "POST"]
    assert fixture.requests[0][1] == "/cgi-bin/getinfo?FILE=1"
    assert fixture.requests[1][1] == "/onvif/device_service"

    assert http_snapshot_calls == ["onvif_http"]
    assert snapshot.failure is SnapshotFailure.TARGET_REJECTED
    # ONVIF HTTP is stubbed; RTSP is the productive provider and its disabled
    # guard is observed through the real service result.
    assert len(snapshot.attempts) == 2
    assert [attempt.method for attempt in snapshot.attempts] == [
        SnapshotMethod.ONVIF_HTTP,
        SnapshotMethod.RTSP_FRAME,
    ]
    assert [attempt.failure for attempt in snapshot.attempts] == [
        SnapshotFailure.UNSUPPORTED,
        SnapshotFailure.TARGET_REJECTED,
    ]
    assert not any(attempt.success for attempt in snapshot.attempts)
    assert media_tripwires == []

    rendered = f"{ui.rendered_text}\n{report!r}\n{result!r}\n{snapshot!r}"
    assert _USERNAME not in rendered
    assert _PASSWORD not in rendered
