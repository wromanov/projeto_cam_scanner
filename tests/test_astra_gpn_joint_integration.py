"""G-PN-JOINT offline acceptance through the real application path.

All network traffic is confined to a loopback HTTPS fixture. The registry,
collector, Panasonic adapter, workflows, inventory service, and MULTI Excel
reader/writer are production implementations; only the UI boundary is shimmed.
"""
from __future__ import annotations

import ssl
import threading
from dataclasses import fields
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Self
from urllib.parse import urlsplit
from zipfile import ZipFile

import openpyxl
import pytest
from requests.adapters import HTTPAdapter

from cam_scanner.application.inventory_service import InventoryService
from cam_scanner.application.multi_workflow import MultiWorkflow
from cam_scanner.application.single_workflow import SingleWorkflow
from cam_scanner.cameras.registry import build_default_registry
from cam_scanner.cameras.strategy import VendorFirstCollector
from cam_scanner.config.models import EffectiveConfig, TransportProfile, TransportRule
from cam_scanner.domain.enums import CollectionStatus, MainMenuChoice
from cam_scanner.domain.models import CameraResult, CameraTarget
from cam_scanner.snapshot.service import SnapshotFailure, SnapshotResult
from cam_scanner.terminal.ui import TerminalUI

_PROFILE = "i-pro-command-interface-v1.17:WV-S2531L"
_USERNAME = "joint-user-sentinel"
_PASSWORD = "joint-password-sentinel"


class _HttpsFixture:
    def __init__(self, scenario: str) -> None:
        self.scenario = scenario
        self.requests: list[dict[str, object]] = []
        self.response_statuses: list[tuple[str, int]] = []
        self._challenge_lock = threading.Lock()
        self._initial_challenge_count = 0
        self._both_initial_challenges = threading.Event()
        self.concurrent_challenge_timeouts = 0
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                owner.requests.append({
                    "method": "GET", "path": self.path,
                    "scheme": "https", "authorization": self.headers.get("Authorization"),
                })
                if self.path.startswith("/cgi-bin/getinfo"):
                    self._cgi()
                    return
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def do_POST(self) -> None:
                body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                if b"GetCapabilities" in body:
                    operation = "GetCapabilities"
                elif b"getSupportedVersions" in body:
                    operation = "getSupportedVersions"
                elif b"getAllUnrestrictedProperties" in body:
                    operation = "getAllUnrestrictedProperties"
                else:
                    operation = "OtherSOAP"
                owner.requests.append({
                    "method": "POST", "path": self.path, "scheme": "https",
                    "operation": operation,
                })
                if owner.scenario == "soap_timeout":
                    threading.Event().wait(0.3)
                status = 403 if owner.scenario == "soap_403" else 404
                owner.response_statuses.append((self.path, status))
                try:
                    self.send_response(status)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def _cgi(self) -> None:
                attempt = sum(1 for req in owner.requests if req["path"] == self.path)
                authorization = self.headers.get("Authorization")
                if owner.scenario == "digest-concurrent" and not authorization:
                    with owner._challenge_lock:
                        owner._initial_challenge_count += 1
                        if owner._initial_challenge_count >= 2:
                            owner._both_initial_challenges.set()
                    if not owner._both_initial_challenges.wait(timeout=2):
                        with owner._challenge_lock:
                            owner.concurrent_challenge_timeouts += 1
                if owner.scenario in {"digest", "digest-concurrent"} and not authorization:
                    self.send_response(401)
                    self.send_header(
                        "WWW-Authenticate",
                        'Digest realm="fixture", nonce="synthetic-nonce", '
                        'qop="auth", algorithm=MD5',
                    )
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                if owner.scenario == "401" and attempt == 1:
                    self.send_response(401)
                    self.send_header(
                        "WWW-Authenticate",
                        'Digest realm="fixture", nonce="synthetic-nonce", '
                        'qop="auth", algorithm=MD5',
                    )
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                if owner.scenario == "401":
                    self.send_response(401)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                if owner.scenario == "403":
                    self.send_response(403)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                if owner.scenario == "404":
                    self.send_response(404)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                if owner.scenario == "timeout":
                    threading.Event().wait(0.5)
                payload = b"NAME=WV-S2531L\nSERIAL=SERIAL-FIXTURE\nVERSION=9.99\n"
                if owner.scenario == "digest-concurrent" and authorization:
                    if 'username="multi-user-a"' in authorization:
                        payload = b"NAME=WV-S2531L\nSERIAL=MULTI-SERIAL-A\nVERSION=9.99\n"
                    elif 'username="multi-user-b"' in authorization:
                        payload = b"NAME=WV-S2531L\nSERIAL=MULTI-SERIAL-B\nVERSION=9.99\n"
                elif owner.scenario == "empty":
                    payload = b""
                elif owner.scenario == "invalid_xml":
                    payload = b"<DeviceInfo><Model>WV-S2531L</Model>"
                elif owner.scenario == "invalid_text":
                    payload = b"camera identity response is not key-value text"
                elif owner.scenario == "similar_names":
                    payload = b"MODE=WV-S2531L\nSERIALNO=SERIAL-FIXTURE\nVERSIONING=9.99\n"
                elif owner.scenario == "firmware_unknown":
                    payload = b"NAME=WV-S2531L\nSERIAL=SERIAL-FIXTURE\n"
                elif owner.scenario == "partial_model_missing":
                    payload = b"SERIAL=SERIAL-FIXTURE\n"
                elif owner.scenario == "model_mismatch":
                    payload = b"NAME=WV-S2531M\nSERIAL=SERIAL-FIXTURE\nVERSION=9.99\n"
                elif owner.scenario == "partial":
                    payload = b"NAME=WV-S2531L\nSERIAL=SERIAL-FIXTURE\nVERSION=9.99\n"
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                try:
                    self.wfile.write(payload)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass

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


class _HttpFixture:
    """Plain HTTP Axis fixture bound only to a second loopback address."""

    def __init__(self) -> None:
        self.requests: list[dict[str, object]] = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                if b"getSupportedVersions" in body:
                    operation = "getSupportedVersions"
                    payload = b'{"data":{"apiVersions":["1.2"]}}'
                elif b"getAllUnrestrictedProperties" in body:
                    operation = "getAllUnrestrictedProperties"
                    payload = (
                        b'{"data":{"propertyList":{"Brand":"Axis Communications",'
                        b'"SerialNumber":"SERIAL-HTTP-PROFILE","Version":"10.1",'
                        b'"ProdFullName":"AXIS P14"}}}'
                    )
                else:
                    operation = "unknown"
                    payload = b""
                owner.requests.append({
                    "method": "POST", "path": self.path, "scheme": "http",
                    "operation": operation,
                    "authorization": self.headers.get("Authorization"),
                })
                if self.path != "/axis-cgi/basicdeviceinfo.cgi" or not payload:
                    self.send_response(404)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *_args: object) -> None:
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.2", 0), Handler)
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


def _inventory(
    port: int, *, request_timeout: float = 7.0, camera_deadline: float = 45.0,
) -> InventoryService:
    config = EffectiveConfig(
        request_timeout_seconds=request_timeout,
        camera_soft_deadline_seconds=camera_deadline,
        transport_rules=tuple(
            TransportRule("127.0.0.1", component, "https", None, port)
            for component in ("vendor_panasonic", "onvif_device")
        ),
    )
    return InventoryService(
        VendorFirstCollector(registry=build_default_registry()), config=config
    )


class _SingleUI:
    def __init__(self, model: str | None, manufacturer: str = "Panasonic") -> None:
        self.model = model
        self.manufacturer = manufacturer
        self.report = None
        self.outputs: list[str] = []

    def prompt_camera_target(self) -> CameraTarget:
        return CameraTarget("127.0.0.1", _USERNAME, _PASSWORD)

    def prompt_manufacturer_hint(self) -> str:
        return self.manufacturer

    def prompt_model_hint(self) -> str | None:
        return self.model

    def prompt_transport_selection(self, _options) -> str:
        return "HTTPS_DEFAULT"

    def render_report(self, report, **_kwargs) -> None:
        self.report = report
        self.outputs.append(repr(report))

    def post_query_menu(self) -> MainMenuChoice:
        return MainMenuChoice.EXIT


class _MultiUI:
    def __init__(
        self, source: Path, destination: Path, selection_id: str = "HTTPS_DEFAULT",
    ) -> None:
        self.source, self.destination = source, destination
        self.selection_id = selection_id
        self.options = ()
        self.outputs: list[str] = []

    def prompt_multi_input_path(self) -> str:
        return str(self.source)

    def prompt_multi_output_path(self, _default: str) -> str:
        return str(self.destination)

    def prompt_transport_selection(self, options) -> str:
        self.options = tuple(options)
        return self.selection_id

    def show_multi_complete(self, path: Path, total: int, *, failed: int) -> None:
        self.outputs.append(f"{path.name}:{total}:{failed}")

    def show_multi_error(self, message: str) -> None:
        self.outputs.append(message)


class _Progress:
    def start(self, _total: int) -> None: pass
    def advance(self, _ip: str, _status: str) -> None: pass
    def finish(self) -> None: pass


class _NoMedia:
    def capture_one(self, *_args: object, **_kwargs: object) -> SnapshotResult:
        return SnapshotResult(failure=SnapshotFailure.UNSUPPORTED)


def _assert_sentinels_absent(value: object) -> None:
    text = str(value)
    assert _USERNAME not in text
    assert _PASSWORD not in text


def test_exact_model_single_workflow_uses_real_default_panasonic_adapter(monkeypatch) -> None:
    with _HttpsFixture("partial") as server:
        _trust_fixture_ca(monkeypatch, server.port)
        ui = _SingleUI("WV-S2531L")
        assert SingleWorkflow(ui, _inventory(server.port), _NoMedia()).run() is MainMenuChoice.EXIT

    report = ui.report
    assert report is not None
    result = report.to_camera_result("127.0.0.1")
    assert result.status is CollectionStatus.PARTIAL_SUCCESS, [
        (a.operation, a.protocol, a.http_status, a.error_category, dict(a.metadata))
        for a in report.attempts
    ]
    assert (result.manufacturer, result.model, result.serial, result.firmware) == (
        None, "WV-S2531L", "SERIAL-FIXTURE", "9.99",
    )
    assert not any(item.get("operation") == "GetCapabilities" for item in server.requests)
    assert [item["path"] for item in server.requests] == [
        "/cgi-bin/getinfo?FILE=1", "/onvif/device_service",
    ]
    assert server.requests[0]["scheme"] == "https"
    cgi_attempt = next(a for a in report.attempts if a.operation == "GET /cgi-bin/getinfo")
    assert cgi_attempt.http_status == 200
    assert cgi_attempt.error_category is None
    assert len(fields(CameraResult)) == 14
    _assert_sentinels_absent(ui.outputs)
    _assert_sentinels_absent(report)


def test_unknown_firmware_remains_unknown_in_exact_model_response(monkeypatch) -> None:
    with _HttpsFixture("firmware_unknown") as server:
        _trust_fixture_ca(monkeypatch, server.port)
        ui = _SingleUI("WV-S2531L")
        SingleWorkflow(ui, _inventory(server.port), _NoMedia()).run()

    assert ui.report.to_camera_result("127.0.0.1").firmware is None
    cgi_attempt = next(a for a in ui.report.attempts if a.operation == "GET /cgi-bin/getinfo")
    assert cgi_attempt.http_status == 200 and cgi_attempt.error_category is None


def test_model_hint_does_not_fill_unobserved_model_or_manufacturer(monkeypatch) -> None:
    with _HttpsFixture("partial_model_missing") as server:
        _trust_fixture_ca(monkeypatch, server.port)
        ui = _SingleUI("WV-S2531L")
        SingleWorkflow(ui, _inventory(server.port), _NoMedia()).run()

    result = ui.report.to_camera_result("127.0.0.1")
    assert result.model is None and result.manufacturer is None
    assert result.serial == "SERIAL-FIXTURE"
    _assert_sentinels_absent(ui.outputs)


@pytest.mark.parametrize("model", [None, "unknown-model", "WV-S2531", "WV-S2531M"])
def test_ineligible_model_does_not_call_panasonic_cgi_or_capabilities(monkeypatch, model) -> None:
    with _HttpsFixture("partial") as server:
        _trust_fixture_ca(monkeypatch, server.port)
        ui = _SingleUI(model)
        SingleWorkflow(ui, _inventory(server.port), _NoMedia()).run()

    assert not any(item["path"].startswith("/cgi-bin/") for item in server.requests)
    capability_calls = [item for item in server.requests
                        if item.get("operation") == "GetCapabilities"]
    assert not capability_calls, {
        "requests": [(item["method"], item["path"], item["scheme"], item.get("operation"))
                     for item in server.requests],
        "attempts": [
            (a.operation, a.protocol, a.http_status, a.error_category, a.outcome)
            for a in ui.report.attempts
        ] if ui.report is not None else [],
    }
    assert not server.requests
    _assert_sentinels_absent(ui.outputs)


@pytest.mark.parametrize(
    "scenario", ["empty", "invalid_xml", "invalid_text", "similar_names"],
)
def test_invalid_panasonic_payload_never_fabricates_identity(
    monkeypatch, scenario: str,
) -> None:
    with _HttpsFixture(scenario) as server:
        _trust_fixture_ca(monkeypatch, server.port)
        ui = _SingleUI("WV-S2531L")
        SingleWorkflow(ui, _inventory(server.port), _NoMedia()).run()

    report = ui.report
    assert report is not None
    cgi = [attempt for attempt in report.attempts
           if attempt.operation == "GET /cgi-bin/getinfo"]
    assert len(cgi) == 1
    assert cgi[0].http_status == 200
    assert cgi[0].error_category == "INVALID_RESPONSE"
    result = report.to_camera_result("127.0.0.1")
    assert (result.manufacturer, result.model, result.serial, result.firmware) == (
        None, None, None, None,
    )
    assert not report.evidence
    assert len([item for item in server.requests
                if item["path"] == "/cgi-bin/getinfo?FILE=1"]) == 1
    _assert_sentinels_absent(ui.outputs)


@pytest.mark.parametrize(
    ("scenario", "status", "category"),
    [("404", 404, "ENDPOINT_UNSUPPORTED"), ("401", 401, "AUTH_REJECTED"),
     ("403", 403, "AUTHORIZATION_DENIED")],
)
def test_cgi_http_statuses_are_reported_without_fallback(monkeypatch, scenario, status, category):
    with _HttpsFixture(scenario) as server:
        _trust_fixture_ca(monkeypatch, server.port)
        ui = _SingleUI("WV-S2531L")
        SingleWorkflow(ui, _inventory(server.port), _NoMedia()).run()

    report = ui.report
    assert report is not None
    relevant = [attempt for attempt in report.attempts if attempt.operation == "GET /cgi-bin/getinfo"]
    assert relevant
    assert relevant[-1].http_status == status
    assert relevant[-1].error_category == category
    assert not report.evidence
    result = report.to_camera_result("127.0.0.1")
    assert (result.manufacturer, result.model, result.serial, result.firmware) == (
        None, None, None, None,
    )
    assert server.requests[0]["path"] == "/cgi-bin/getinfo?FILE=1"
    assert len([item for item in server.requests if str(item["path"]).startswith("/cgi-bin/")]) == (
        2 if scenario == "401" else 1
    )
    _assert_sentinels_absent(ui.outputs)


def test_digest_challenge_then_200_records_both_exchanges_and_effective_https(monkeypatch) -> None:
    with _HttpsFixture("digest") as server:
        _trust_fixture_ca(monkeypatch, server.port)
        ui = _SingleUI("WV-S2531L")
        SingleWorkflow(ui, _inventory(server.port), _NoMedia()).run()

    assert [item["scheme"] for item in server.requests] == ["https", "https", "https"]
    assert [item["path"] for item in server.requests] == [
        "/cgi-bin/getinfo?FILE=1", "/cgi-bin/getinfo?FILE=1", "/onvif/device_service",
    ]
    assert server.requests[0]["authorization"] is None
    assert str(server.requests[1]["authorization"]).startswith("Digest ")
    cgi_attempt = next(a for a in ui.report.attempts if a.operation == "GET /cgi-bin/getinfo")
    assert cgi_attempt.http_status == 200
    assert cgi_attempt.error_category is None
    _assert_sentinels_absent(ui.outputs)


def test_multi_profile_applies_only_to_loopback_member_and_other_target_stays_https(
    monkeypatch, tmp_path: Path,
) -> None:
    with _HttpFixture() as member, _HttpsFixture("404") as outside:
        _trust_fixture_ca(monkeypatch, outside.port)
        profile = TransportProfile(
            "axis-public-local", ("127.0.0.2",), "vendor_axis", "http", member.port,
            "PUBLIC_NONE", "AUTH-LOCAL-01", True,
        )
        config = EffectiveConfig(
            transport_rules=tuple(
                TransportRule("127.0.0.1", component, "https", None, outside.port)
                for component in ("vendor_axis", "onvif_device")
            ),
            transport_profiles=(profile,),
        )
        service = InventoryService(
            VendorFirstCollector(registry=build_default_registry()), config=config
        )
        source, destination = tmp_path / "input.xlsx", tmp_path / "result.xlsx"
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(("IP", "USERNAME", "PASSWORD", "FABRICANTE", "MODELO"))
        sheet.append(("127.0.0.2", "profile-user", "profile-secret", "Axis", None))
        sheet.append(("127.0.0.1", "default-user", "default-secret", "Axis", None))
        workbook.save(source)
        workbook.close()
        ui = _MultiUI(source, destination, selection_id=profile.id)
        workflow = MultiWorkflow(
            ui, service, _NoMedia(), progress_reporter=_Progress(), max_workers=1,
        )

        workflow.run()

    assert ui.outputs and ui.outputs[0].startswith("result.xlsx:2:")
    assert len(workflow.completed_rows) == 2
    profile_row, outside_row = workflow.completed_rows
    assert (profile_row.result.manufacturer, profile_row.result.model,
            profile_row.result.serial, profile_row.result.firmware) == (
        "Axis Communications", "AXIS P14", "SERIAL-HTTP-PROFILE", "10.1",
    )
    assert (profile_row.result.status, outside_row.result.ip) == (
        CollectionStatus.SUCCESS, "127.0.0.1",
    )
    assert profile_row.result.hardware_id is None
    assert {item.protocol for item in profile_row.report.evidence} == {"HTTP"}
    option = next(item for item in ui.options if item.selection_id == profile.id)
    assert (option.http_rows, option.https_rows, option.ineligible_rows) == (1, 1, 0)

    assert len(member.requests) == 2
    assert [item["operation"] for item in member.requests] == [
        "getSupportedVersions", "getAllUnrestrictedProperties",
    ]
    assert all(
        item["scheme"] == "http"
        and item["path"] == "/axis-cgi/basicdeviceinfo.cgi"
        and item["authorization"] is None
        for item in member.requests
    )
    assert outside.requests
    assert all(item["scheme"] == "https" for item in outside.requests)
    assert outside.requests[0]["path"] == "/axis-cgi/basicdeviceinfo.cgi"

    profile_attempt = next(
        item for item in profile_row.report.attempts
        if item.operation.endswith("getAllUnrestrictedProperties")
    )
    outside_attempt = next(
        item for item in outside_row.report.attempts
        if item.operation.endswith("getSupportedVersions")
    )
    assert profile_attempt.protocol == "HTTP"
    assert {
        key: profile_attempt.metadata[key]
        for key in ("policy_id", "authorization_ref", "auth_mode", "scheme")
    } == {
        "policy_id": profile.id,
        "authorization_ref": profile.authorization_ref,
        "auth_mode": "PUBLIC_NONE",
        "scheme": "http",
    }
    assert outside_attempt.protocol == "HTTPS"
    assert outside_attempt.metadata["policy_id"] == "HTTPS_DEFAULT"
    assert outside_attempt.metadata["scheme"] == "https"

    terminal_lines: list[str] = []
    TerminalUI(output_fn=terminal_lines.append).render_report(
        profile_row.report, ip=profile_row.result.ip, duration=0.0,
        snapshot=profile_row.snapshot,
    )
    profile_diagnostic = next(line for line in terminal_lines
                              if "getAllUnrestrictedProperties" in line)
    assert all(value in profile_diagnostic for value in (
        "HTTP.POST /axis-cgi/basicdeviceinfo.cgi",
        f"política {profile.id}",
        f"referência {profile.authorization_ref}",
        "auth PUBLIC_NONE",
    ))
    assert "profile-user" not in "\n".join(terminal_lines)
    assert "profile-secret" not in "\n".join(terminal_lines)

    output = openpyxl.load_workbook(destination, read_only=True, data_only=False)
    try:
        diagnostics = list(output["DIAGNOSTICOS"].iter_rows(values_only=True))
        assert len(fields(CameraResult)) == 14
        assert len(diagnostics[0]) == 9
        profile_diag = next(
            row for row in diagnostics[1:]
            if row[0] == profile_row.source_row
            and row[3] == profile_attempt.operation
        )
        outside_diag = next(
            row for row in diagnostics[1:]
            if row[0] == outside_row.source_row
            and row[3] == outside_attempt.operation
        )
        assert (profile_diag[2], outside_diag[2]) == ("HTTP", "HTTPS")
        serialized = "\n".join(
            str(value)
            for sheet in output.worksheets
            for row in sheet.iter_rows(values_only=True)
            for value in row
            if value is not None
        )
        for canary in (
            "profile-user", "profile-secret", "default-user", "default-secret",
        ):
            assert canary not in serialized
    finally:
        output.close()


def test_multi_real_excel_path_isolates_credentials_for_same_ip_and_sanitizes_output(
    monkeypatch, tmp_path: Path,
) -> None:
    with _HttpsFixture("digest-concurrent") as server:
        _trust_fixture_ca(monkeypatch, server.port)
        source, destination = tmp_path / "input.xlsx", tmp_path / "result.xlsx"
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(("IP", "USERNAME", "PASSWORD", "FABRICANTE", "MODELO"))
        sheet.append(("127.0.0.1", "multi-user-a", "multi-secret-a", "Panasonic", "WV-S2531L"))
        sheet.append(("127.0.0.1", "multi-user-b", "multi-secret-b", "Panasonic", "WV-S2531L"))
        workbook.save(source)
        workbook.close()
        ui = _MultiUI(source, destination)
        inventory = _CapturingInventory(_inventory(server.port))
        workflow = MultiWorkflow(
            ui, inventory, _NoMedia(), progress_reporter=_Progress(), max_workers=2,
        )
        workflow.run()

    cgi = [item for item in server.requests if str(item["path"]).startswith("/cgi-bin/")]
    assert len(cgi) == 4
    unauthenticated = [item for item in cgi if item["authorization"] is None]
    authenticated = [item for item in cgi if str(item["authorization"]).startswith("Digest ")]
    assert len(unauthenticated) == len(authenticated) == 2
    assert server._both_initial_challenges.is_set()
    assert server.concurrent_challenge_timeouts == 0
    assert any('username="multi-user-a"' in str(item["authorization"])
               for item in authenticated)
    assert any('username="multi-user-b"' in str(item["authorization"])
               for item in authenticated)
    assert [row.result.status for row in workflow.completed_rows] == [
        CollectionStatus.PARTIAL_SUCCESS, CollectionStatus.PARTIAL_SUCCESS,
    ]
    assert [row.result.serial for row in workflow.completed_rows] == [
        "MULTI-SERIAL-A", "MULTI-SERIAL-B",
    ]
    assert len(inventory.contexts) == 2
    assert inventory.contexts[0] is not inventory.contexts[1]
    assert inventory.contexts[0].auth is not inventory.contexts[1].auth
    assert {context.target.ip for context in inventory.contexts} == {"127.0.0.1"}
    ledger_states = [
        (context.auth.logical_attempts, context.auth.physical_exchanges,
         context.auth.state)
        for context in inventory.contexts
    ]
    assert ledger_states[0] == ledger_states[1]
    assert ledger_states[0][0] <= 2
    assert ledger_states[0][1] >= 2
    assert len(fields(CameraResult)) == 14
    output = openpyxl.load_workbook(destination, data_only=False)
    try:
        values = [cell for row in output.active.iter_rows() for cell in row]
        serialized = "\n".join(str(cell.value) for cell in values if cell.value is not None)
        assert _USERNAME not in serialized and _PASSWORD not in serialized
        assert "multi-user-a" not in serialized and "multi-user-b" not in serialized
        assert "multi-secret-a" not in serialized and "multi-secret-b" not in serialized
        assert sum(1 for row in output.active.iter_rows(min_row=2) if row[0].value is not None) == 2
    finally:
        output.close()
    assert all(item["scheme"] == "https" for item in server.requests)
    _assert_sentinels_absent(ui.outputs)


def test_multi_legacy_workbook_exports_mixed_rows_and_rejects_formula_model_hint(
    monkeypatch, tmp_path: Path,
) -> None:
    with _HttpsFixture("partial") as server:
        _trust_fixture_ca(monkeypatch, server.port)
        source, destination = tmp_path / "legacy-input.xlsx", tmp_path / "legacy-output.xlsx"
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(("IP", "USERNAME", "PASSWORD", "LEGACY_NOTES", "FABRICANTE", "MODELO"))
        sheet.append((
            "127.0.0.1", "formula-user", "formula-secret", "legacy extra",
            "Panasonic", '=\"WV-S2531L\"',
        ))
        sheet.append((
            "not-an-ip", "invalid-user", "invalid-secret", "legacy extra",
            "Panasonic", "WV-S2531L",
        ))
        sheet.append((
            "127.0.0.1", "valid-user", "valid-secret", "legacy extra",
            "Panasonic", "WV-S2531L",
        ))
        workbook.save(source)
        workbook.close()

        with ZipFile(source, "r") as archive:
            entries = [(entry, archive.read(entry.filename)) for entry in archive.infolist()]
        old_cell = b'<c r="F2"><f>"WV-S2531L"</f><v></v></c>'
        cached_cell = b'<c r="F2" t="str"><f>"WV-S2531L"</f><v>WV-S2531L</v></c>'
        for index, (entry, content) in enumerate(entries):
            if entry.filename == "xl/worksheets/sheet1.xml":
                assert old_cell in content
                entries[index] = (entry, content.replace(old_cell, cached_cell, 1))
                break
        else:
            pytest.fail("A planilha legada sintética não contém a primeira aba esperada.")
        with ZipFile(source, "w") as archive:
            for entry, content in entries:
                archive.writestr(entry, content)

        ui = _MultiUI(source, destination)
        workflow = MultiWorkflow(
            ui, _inventory(server.port), _NoMedia(),
            progress_reporter=_Progress(), max_workers=1,
        )
        workflow.run()

    assert ui.outputs and ui.outputs[0].startswith("legacy-output.xlsx:3:")
    assert len(workflow.completed_rows) == 3
    formula_row, invalid_row, valid_row = workflow.completed_rows
    assert [row.source_row for row in workflow.completed_rows] == [2, 3, 4]
    assert formula_row.result.status is CollectionStatus.FAILED
    assert invalid_row.result.status is CollectionStatus.FAILED
    assert valid_row.result.status is CollectionStatus.PARTIAL_SUCCESS
    assert any(
        attempt.operation == "validate_model_hint"
        and attempt.error_category == "INVALID_INPUT"
        for attempt in formula_row.report.attempts
    )
    cgi_requests = [
        request for request in server.requests
        if str(request["path"]).startswith("/cgi-bin/getinfo")
    ]
    assert len(cgi_requests) == 1
    assert all(request["scheme"] == "https" for request in server.requests)

    output = openpyxl.load_workbook(destination, data_only=False)
    try:
        inventory_rows = list(output.active.iter_rows(min_row=2, values_only=True))
        assert [row[0] for row in inventory_rows] == [2, 3, 4]
        diagnostics = list(output["DIAGNOSTICOS"].iter_rows(values_only=True))
        assert len(diagnostics[0]) == 9
        assert any(
            row[0] == 2 and row[3] == "validate_model_hint" and row[5] == "INVALID_INPUT"
            for row in diagnostics[1:]
        )
        serialized = "\n".join(
            str(cell.value)
            for sheet in output.worksheets
            for row in sheet.iter_rows()
            for cell in row
            if cell.value is not None
        )
        for secret in ("formula-user", "formula-secret", "invalid-user", "invalid-secret",
                       "valid-user", "valid-secret"):
            assert secret not in serialized
        assert all(
            cell.data_type != "f"
            for sheet in output.worksheets
            for row in sheet.iter_rows()
            for cell in row
        )
    finally:
        output.close()


def test_invalid_tls_is_fail_closed_without_http_fallback() -> None:
    with _HttpsFixture("partial") as server:
        ui = _SingleUI("WV-S2531L")
        SingleWorkflow(ui, _inventory(server.port), _NoMedia()).run()

    report = ui.report
    assert report is not None
    failures = [attempt for attempt in report.attempts if attempt.error_category == "TLS_ERROR"]
    assert failures
    assert all(item["scheme"] == "https" for item in server.requests)
    assert not any(item["path"] == "/onvif/device_service" for item in server.requests)
    _assert_sentinels_absent(ui.outputs)


def test_request_timeout_is_classified_and_preserves_request_sequence(monkeypatch) -> None:
    with _HttpsFixture("timeout") as server:
        _trust_fixture_ca(monkeypatch, server.port)
        ui = _SingleUI("WV-S2531L")
        SingleWorkflow(
            ui, _inventory(server.port, request_timeout=0.1), _NoMedia(),
        ).run()

    report = ui.report
    assert report is not None
    assert any(attempt.error_category in {"READ_TIMEOUT", "CONNECT_TIMEOUT"}
               for attempt in report.attempts)
    assert server.requests[0]["path"] == "/cgi-bin/getinfo?FILE=1"
    assert all(item["scheme"] == "https" for item in server.requests)
    _assert_sentinels_absent(ui.outputs)


def test_expired_deadline_and_cancelled_context_make_no_network_request(monkeypatch) -> None:
    with _HttpsFixture("partial") as server:
        _trust_fixture_ca(monkeypatch, server.port)
        service = _inventory(server.port, camera_deadline=0.05)
        target = CameraTarget("127.0.0.1", _USERNAME, _PASSWORD)
        context = service.create_context(
            target, manufacturer_hint="Panasonic", model_hint="WV-S2531L",
        )
        threading.Event().wait(0.06)
        try:
            report, _ = service.collect_execution(target, context=context)
        finally:
            context.close()
        assert any(attempt.error_category in {"DEADLINE_EXCEEDED", "CONNECT_TIMEOUT"}
                   for attempt in report.attempts)
        assert not server.requests

        cancel_event = threading.Event()
        cancel_event.set()
        cancelled, cancel_context = service.collect_execution(
            target, cancel_event=cancel_event,
            manufacturer_hint="Panasonic", model_hint="WV-S2531L",
        )
        try:
            assert cancelled.status is CollectionStatus.CANCELLED
        finally:
            cancel_context.close()
    assert not server.requests


class _CapturingInventory:
    """Capture returned row contexts while retaining the production service."""

    def __init__(self, service: InventoryService) -> None:
        self.service = service
        self.contexts = []

    def __getattr__(self, name: str):
        return getattr(self.service, name)

    def collect_execution(self, *args, **kwargs):
        report, context = self.service.collect_execution(*args, **kwargs)
        self.contexts.append(context)
        return report, context


def _run_single_model_case(monkeypatch, scenario: str):
    with _HttpsFixture(scenario) as server:
        _trust_fixture_ca(monkeypatch, server.port)
        inventory = _CapturingInventory(_inventory(server.port))
        ui = _SingleUI("WV-S2531L")
        SingleWorkflow(ui, inventory, _NoMedia()).run()
        assert ui.report is not None
        context = inventory.contexts[0]
        return ui.report.to_camera_result("127.0.0.1"), list(server.requests), (
            context.auth.logical_attempts,
            context.auth.physical_exchanges,
            context.auth.state,
        )


def _run_multi_model_case(monkeypatch, tmp_path: Path, scenario: str):
    with _HttpsFixture(scenario) as server:
        _trust_fixture_ca(monkeypatch, server.port)
        source = tmp_path / f"{scenario}-input.xlsx"
        destination = tmp_path / f"{scenario}-output.xlsx"
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(("IP", "USERNAME", "PASSWORD", "FABRICANTE", "MODELO"))
        sheet.append(("127.0.0.1", _USERNAME, _PASSWORD, "Panasonic", "WV-S2531L"))
        workbook.save(source)
        workbook.close()

        inventory = _CapturingInventory(_inventory(server.port))
        ui = _MultiUI(source, destination)
        workflow = MultiWorkflow(
            ui, inventory, _NoMedia(), progress_reporter=_Progress(), max_workers=1,
        )
        workflow.run()
        assert len(workflow.completed_rows) == 1
        row = workflow.completed_rows[0]
        context = inventory.contexts[0]
        evidence = (
            row.result,
            list(server.requests),
            (
                context.auth.logical_attempts,
                context.auth.physical_exchanges,
                context.auth.state,
            ),
        )
        return evidence


def test_model_hint_mismatch_preserves_observed_identity_without_new_requests_or_auth(
    monkeypatch, tmp_path: Path,
) -> None:
    single_match = _run_single_model_case(monkeypatch, "partial")
    single_mismatch = _run_single_model_case(monkeypatch, "model_mismatch")
    multi_match = _run_multi_model_case(monkeypatch, tmp_path, "partial")
    multi_mismatch = _run_multi_model_case(monkeypatch, tmp_path, "model_mismatch")

    for matched, mismatched in (
        (single_match, single_mismatch),
        (multi_match, multi_mismatch),
    ):
        _matched_result, matched_requests, matched_auth = matched
        mismatch_result, mismatch_requests, mismatch_auth = mismatched
        assert mismatch_result.model == "WV-S2531M"
        assert mismatch_result.model != "WV-S2531L"
        assert mismatch_result.serial == "SERIAL-FIXTURE"
        assert mismatch_result.firmware == "9.99"
        assert len(mismatch_requests) == len(matched_requests)
        assert [
            (item["method"], item["path"], item["scheme"], item.get("authorization"))
            for item in mismatch_requests
        ] == [
            (item["method"], item["path"], item["scheme"], item.get("authorization"))
            for item in matched_requests
        ]
        assert mismatch_auth == matched_auth
        assert mismatch_auth == matched_auth
        assert not any(item.get("authorization") for item in mismatch_requests)


@pytest.mark.parametrize(
    ("scenario", "expected_category", "expected_status"),
    [("soap_403", "SOAP_FAULT", 403), ("soap_timeout", "READ_TIMEOUT", None)],
)
def test_panasonic_partial_evidence_survives_later_onvif_denial_or_timeout(
    monkeypatch, scenario: str, expected_category: str, expected_status: int | None,
) -> None:
    with _HttpsFixture(scenario) as server:
        _trust_fixture_ca(monkeypatch, server.port)
        inventory = _CapturingInventory(_inventory(
            server.port, request_timeout=0.1 if scenario == "soap_timeout" else 7.0,
        ))
        ui = _SingleUI("WV-S2531L")
        SingleWorkflow(ui, inventory, _NoMedia()).run()
        response_statuses = list(server.response_statuses)

    report = ui.report
    assert report is not None
    result = report.to_camera_result("127.0.0.1")
    assert result.status is CollectionStatus.PARTIAL_SUCCESS
    assert (result.model, result.serial, result.firmware) == (
        "WV-S2531L", "SERIAL-FIXTURE", "9.99",
    )
    assert result.manufacturer is None
    provenance = {
        (item.field, item.source, item.protocol, item.operation)
        for item in report.evidence
    }
    assert {
        ("model", "VENDOR", "HTTPS", "GET /cgi-bin/getinfo"),
        ("serial", "VENDOR", "HTTPS", "GET /cgi-bin/getinfo"),
        ("firmware", "VENDOR", "HTTPS", "GET /cgi-bin/getinfo"),
    } <= provenance
    if expected_status is not None:
        assert response_statuses[-1] == ("/onvif/device_service", expected_status)
    cgi_index = next(
        index for index, attempt in enumerate(report.attempts)
        if attempt.operation == "GET /cgi-bin/getinfo"
    )
    later_failure = next(
        (index, attempt) for index, attempt in enumerate(report.attempts)
        if index > cgi_index and attempt.error_category is not None
    )
    assert later_failure[1].error_category == expected_category
    if expected_status is None:
        assert later_failure[1].http_status is None
    assert [item["path"] for item in server.requests] == [
        "/cgi-bin/getinfo?FILE=1", "/onvif/device_service",
    ]


@pytest.mark.parametrize(
    ("scenario", "expected_stage", "expected_category"),
    [
        ("empty", "PARSE", "INVALID_RESPONSE"),
        ("401", "AUTH", "AUTH_REJECTED"),
        ("403", "AUTH", "AUTHORIZATION_DENIED"),
        ("404", "HTTP", "ENDPOINT_UNSUPPORTED"),
        ("timeout", "HTTP", "READ_TIMEOUT"),
        ("tls_invalid", "CONNECT", "TLS_ERROR"),
        ("soap_403", "SOAP", "SOAP_FAULT"),
    ],
)
def test_single_workflow_diagnostic_scenario_matrix_is_stage_specific_and_sanitized(
    monkeypatch, scenario: str, expected_stage: str, expected_category: str,
) -> None:
    with _HttpsFixture(scenario) as server:
        if scenario != "tls_invalid":
            _trust_fixture_ca(monkeypatch, server.port)
        inventory = _inventory(
            server.port,
            request_timeout=0.1 if scenario == "timeout" else 7.0,
        )
        ui = _SingleUI("WV-S2531L")
        SingleWorkflow(ui, inventory, _NoMedia()).run()

    report = ui.report
    assert report is not None
    assert any(
        attempt.stage == expected_stage and attempt.error_category == expected_category
        for attempt in report.attempts
    ), [
        (attempt.stage, attempt.operation, attempt.http_status, attempt.error_category)
        for attempt in report.attempts
    ]
    _assert_sentinels_absent(report)
    _assert_sentinels_absent(ui.outputs)
