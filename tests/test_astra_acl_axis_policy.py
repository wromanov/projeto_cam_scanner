from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Self

import pytest

from cam_scanner.application.collection_context import CollectionContext
from cam_scanner.cameras.manufacturers.axis import AxisAdapter
from cam_scanner.cameras.transport import TargetTransportPolicy
from cam_scanner.config.models import EffectiveConfig, TransportRule
from cam_scanner.config.transport_plan import select_transport
from cam_scanner.domain.enums import CollectionStatus
from cam_scanner.domain.models import CameraTarget

_LOOPBACK = "127.0.0.1"
_PATH = "/axis-cgi/basicdeviceinfo.cgi"
_VERSIONS = "getSupportedVersions"
_UNRESTRICTED = "getAllUnrestrictedProperties"
_OPERATOR = "getAllProperties"
_SCENARIO_PROFILES = ("Viewer", "Operator", "Administrator")


@dataclass(frozen=True)
class _ObservedRequest:
    operation: str
    status: int
    authorization_present: bool
    cookie_present: bool
    body: bytes


class _LoopbackServer:
    def __init__(self, handler: type[BaseHTTPRequestHandler]) -> None:
        self.httpd = ThreadingHTTPServer((_LOOPBACK, 0), handler)
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


@contextmanager
def _axis_fixture(*, challenge_on_versions: bool = False) -> Iterator[
    tuple[_LoopbackServer, list[_ObservedRequest]]
]:
    observed: list[_ObservedRequest] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            try:
                payload = json.loads(body)
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = {}
            operation = payload.get("method", "") if isinstance(payload, dict) else ""

            if self.path != _PATH:
                status, response_body = 404, b""
            elif operation == _VERSIONS and challenge_on_versions:
                status, response_body = 401, b""
                self.send_response(status)
                self.send_header(
                    "WWW-Authenticate",
                    'Digest realm="loopback-fixture", nonce="fixture-nonce", '
                    'qop="auth", opaque="fixture-opaque"',
                )
                self.send_header("Content-Length", "0")
                self.end_headers()
                observed.append(_ObservedRequest(
                    operation, status, "Authorization" in self.headers,
                    "Cookie" in self.headers, body,
                ))
                return
            elif operation == _VERSIONS:
                status = 200
                response_body = json.dumps({"data": {"apiVersions": ["1.2"]}}).encode()
            elif operation == _UNRESTRICTED:
                status = 200
                response_body = json.dumps({"data": {"propertyList": {
                    "Brand": "AXIS",
                    "SerialNumber": "FIXTURE-SERIAL",
                    "Version": "FIXTURE-FIRMWARE",
                    "ProdFullName": "AXIS fixture camera",
                }}}).encode()
            elif operation == _OPERATOR:
                status, response_body = 403, b""
            else:
                status, response_body = 400, b""

            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_body)))
            self.end_headers()
            self.wfile.write(response_body)
            observed.append(_ObservedRequest(
                operation, status, "Authorization" in self.headers,
                "Cookie" in self.headers, body,
            ))

        def log_message(self, _format: str, *_args: object) -> None:
            return

    with _LoopbackServer(Handler) as server:
        yield server, observed


def _target() -> CameraTarget:
    # One fixed, role-neutral username is used for every synthetic scenario.
    return CameraTarget(_LOOPBACK, "fixture-account", "fixture-password")


def _context(server: _LoopbackServer, target: CameraTarget) -> CollectionContext:
    config = EffectiveConfig(transport_rules=(TransportRule(
        target=_LOOPBACK,
        component="vendor_axis",
        protocol="http",
        host=None,
        port=server.port,
    ),))
    config = select_transport(
        config, (target,), {_LOOPBACK: "vendor_axis"}, "LEGACY_EXACT"
    )
    return CollectionContext(
        target,
        config,
        transport_factory=lambda context: TargetTransportPolicy(context),
    )


@pytest.mark.parametrize("scenario_profile", _SCENARIO_PROFILES, ids=str.casefold)
def test_axis_role_labels_do_not_select_operator_or_enable_credentials(
    scenario_profile: str,
) -> None:
    """Scenario labels are not roles inferred by the real Axis adapter or transport."""
    target = _target()
    with _axis_fixture() as (server, observed):
        context = _context(server, target)
        try:
            assert context.transport.endpoint(
                "vendor_axis", path=_PATH
            ) == f"http://{_LOOPBACK}:{server.port}{_PATH}"
            report = AxisAdapter().collect_report(target, context=context)

            assert observed, f"no loopback request; attempts={report.attempts!r}"
            operation_matrix = [
                (scenario_profile, request.operation, request.status)
                for request in observed
            ]
            assert operation_matrix == [
                (scenario_profile, _VERSIONS, 200),
                (scenario_profile, _UNRESTRICTED, 200),
            ]
            assert report.status is CollectionStatus.SUCCESS
            assert [attempt.operation.rsplit(" ", 1)[-1] for attempt in report.attempts] == [
                _UNRESTRICTED,
            ]
            assert len(observed) == 2
            assert _OPERATOR not in [request.operation for request in observed]
            assert not any(
                request.authorization_present or request.cookie_present
                for request in observed
            )
            assert all(
                b"fixture-account" not in request.body
                and b"fixture-password" not in request.body
                for request in observed
            )
            assert context.auth.logical_attempts == 0
            assert all(attempt.authentication_mechanism == "NONE" for attempt in report.attempts)
        finally:
            context.close()


@pytest.mark.parametrize("scenario_profile", _SCENARIO_PROFILES, ids=str.casefold)
def test_axis_credentials_never_replay_after_public_401_challenge(
    scenario_profile: str,
) -> None:
    """A challenge on the public Axis path does not authorize credential replay."""
    target = _target()
    with _axis_fixture(challenge_on_versions=True) as (server, observed):
        context = _context(server, target)
        try:
            report = AxisAdapter().collect_report(target, context=context)

            operation_matrix = [
                (scenario_profile, request.operation, request.status)
                for request in observed
            ]
            assert operation_matrix == [(scenario_profile, _VERSIONS, 401)]
            assert report.status is CollectionStatus.FAILED
            assert len(observed) == 1
            assert report.attempts[0].operation == f"POST {_PATH} {_VERSIONS}"
            assert report.attempts[0].error_category == "HTTP_ERROR"
            assert report.attempts[0].authentication_mechanism == "NONE"
            assert not observed[0].authorization_present
            assert not observed[0].cookie_present
            assert b"fixture-account" not in observed[0].body
            assert b"fixture-password" not in observed[0].body
            assert context.auth.logical_attempts == 0
        finally:
            context.close()
