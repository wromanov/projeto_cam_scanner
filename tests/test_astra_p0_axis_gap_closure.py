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
from cam_scanner.config.models import EffectiveConfig, TransportProfile
from cam_scanner.config.transport_plan import select_transport
from cam_scanner.domain.enums import CollectionStatus
from cam_scanner.domain.models import CameraTarget

_LOOPBACK = "127.0.0.1"
_PATH = "/axis-cgi/basicdeviceinfo.cgi"
_VERSIONS = "getSupportedVersions"
_UNRESTRICTED = "getAllUnrestrictedProperties"
_OPERATOR = "getAllProperties"
_SUPPORTED = json.dumps({"data": {"apiVersions": ["1.2"]}}).encode()
_PROPERTIES = json.dumps({"data": {"propertyList": {
    "Brand": "AXIS",
    "SerialNumber": "LOOPBACK-SERIAL",
    "Version": "LOOPBACK-FIRMWARE",
}}}).encode()
_CHALLENGE = 'Digest realm="loopback-only", nonce="synthetic", qop="auth"'


@dataclass(frozen=True)
class _Reply:
    status: int
    body: bytes = b""
    challenge: bool = False


@dataclass(frozen=True)
class _Request:
    method: str
    path: str
    operation: str
    body: bytes
    authorization: str | None
    cookie: str | None


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
def _axis_fixture(replies: tuple[_Reply, ...]) -> Iterator[
    tuple[_LoopbackServer, list[_Request]]
]:
    requests: list[_Request] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            try:
                payload = json.loads(body)
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = {}
            operation = payload.get("method", "") if isinstance(payload, dict) else ""
            index = len(requests)
            requests.append(_Request(
                self.command, self.path, operation, body,
                self.headers.get("Authorization"), self.headers.get("Cookie"),
            ))
            reply = replies[index] if index < len(replies) else _Reply(500)
            self.send_response(reply.status)
            if reply.challenge:
                self.send_header("WWW-Authenticate", _CHALLENGE)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(reply.body)))
            self.end_headers()
            if reply.body:
                self.wfile.write(reply.body)

        def log_message(self, _format: str, *_args: object) -> None:
            return

    with _LoopbackServer(Handler) as server:
        yield server, requests


def _target(username: str = "fixture-viewer") -> CameraTarget:
    return CameraTarget(_LOOPBACK, username, "synthetic-password-never-sent")


def _context(server: _LoopbackServer, target: CameraTarget) -> CollectionContext:
    profile = TransportProfile(
        id="axis-public-loopback",
        targets=(_LOOPBACK,),
        component="vendor_axis",
        protocol="http",
        port=server.port,
        auth_mode="PUBLIC_NONE",
        authorization_ref="fixture-axis-public",
        http_risk_accepted=True,
    )
    config = select_transport(
        EffectiveConfig(transport_profiles=(profile,)),
        (target,),
        {_LOOPBACK: "vendor_axis"},
        profile.id,
    )
    return CollectionContext(
        target,
        config,
        transport_factory=lambda context: TargetTransportPolicy(context),
    )


def _assert_public_requests(requests: list[_Request]) -> None:
    assert all(request.method == "POST" and request.path == _PATH for request in requests)
    assert all(request.operation != _OPERATOR for request in requests)
    assert all(request.authorization is None and request.cookie is None for request in requests)
    assert all(
        b"synthetic-password-never-sent" not in request.body
        and b"fixture-viewer" not in request.body
        and b"admin" not in request.body
        for request in requests
    )


@pytest.mark.parametrize(
    ("versions_body", "expected_category"),
    [
        pytest.param(b'{"data":{"apiVersions":["1.0"]}}', "ENDPOINT_UNSUPPORTED", id="unsupported-version"),
        pytest.param(b'{"data":{"apiVersions":[]}}', "ENDPOINT_UNSUPPORTED", id="empty-version-list"),
        pytest.param(b'{"data":{"apiVersions":[1.2]}}', "INVALID_RESPONSE", id="malformed-version-item"),
        pytest.param(b'{"data":{}}', "INVALID_RESPONSE", id="missing-version-list"),
        pytest.param(b"not-json", "INVALID_RESPONSE", id="malformed-json"),
    ],
)
def test_axis_unsupported_or_malformed_versions_stop_before_enumeration_or_auth(
    versions_body: bytes, expected_category: str,
) -> None:
    with _axis_fixture((_Reply(200, versions_body), _Reply(200, _PROPERTIES))) as (server, requests):
        target = _target()
        context = _context(server, target)
        try:
            report = AxisAdapter().collect_report(target, context=context)

            assert len(requests) == 1
            assert [request.operation for request in requests] == [_VERSIONS]
            assert report.status is CollectionStatus.FAILED
            assert report.attempts[-1].error_category == expected_category
            assert report.attempts[-1].authentication_mechanism == "NONE"
            assert context.auth.logical_attempts == 0
            _assert_public_requests(requests)
        finally:
            context.close()


def test_axis_reuses_observed_12_without_an_extra_versions_or_operator_request() -> None:
    with _axis_fixture((_Reply(200, _SUPPORTED), _Reply(200, _PROPERTIES))) as (server, requests):
        target = _target()
        context = _context(server, target)
        try:
            report = AxisAdapter().collect_report(target, context=context)

            # This fixture intentionally omits Model, so the collection is partial.
            assert report.status is CollectionStatus.PARTIAL_SUCCESS
            assert [request.operation for request in requests] == [_VERSIONS, _UNRESTRICTED]
            assert len(requests) == 2
            assert json.loads(requests[1].body) == {
                "apiVersion": "1.2", "method": _UNRESTRICTED,
            }
            assert context.auth.logical_attempts == 0
            _assert_public_requests(requests)
        finally:
            context.close()


@pytest.mark.parametrize(
    ("reply", "expected_category"),
    [
        pytest.param(_Reply(200, b'{"error":{"code":2001,"message":"synthetic"}}'),
                     "AUTHORIZATION_DENIED", id="json-2001"),
        pytest.param(_Reply(401), "HTTP_ERROR", id="401-without-challenge"),
        pytest.param(_Reply(401, challenge=True), "HTTP_ERROR", id="401-with-challenge"),
        pytest.param(_Reply(403), "AUTHORIZATION_DENIED", id="403-final"),
    ],
)
def test_axis_public_errors_never_succeed_replay_or_fallback_to_authenticated_request(
    reply: _Reply, expected_category: str,
) -> None:
    with _axis_fixture((reply, _Reply(200, _PROPERTIES), _Reply(200, _PROPERTIES))) as (server, requests):
        target = _target(username="admin")
        context = _context(server, target)
        try:
            plan = context.config.transport_plan
            entry = plan.for_target(_LOOPBACK, "vendor_axis")
            assert entry is not None
            assert plan.selection_id == "axis-public-loopback"
            assert entry.metadata.auth_mode == "PUBLIC_NONE"
            assert entry.metadata.scheme == "http"

            report = AxisAdapter().collect_report(target, context=context)

            assert report.status is CollectionStatus.FAILED
            assert report.attempts[-1].error_category == expected_category
            assert len(requests) == 1
            assert [request.operation for request in requests] == [_VERSIONS]
            assert context.auth.logical_attempts == 0
            assert plan.for_target(_LOOPBACK, "vendor_axis") == entry
            assert entry.metadata.auth_mode == "PUBLIC_NONE"
            _assert_public_requests(requests)
        finally:
            context.close()
