"""Bounded ACL fixture for the sole production Digest operation exercised here.

The HTTP server and its account-to-role ACL are synthetic. The request path is
the real Hikvision adapter and guarded transport; this does not establish a
camera's ACL or cover other operations, because production exposes no
Viewer/Operator/Administrator operation selector.
"""
from __future__ import annotations

import hashlib
import hmac
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Self
from urllib.parse import urlsplit

from requests.utils import parse_dict_header

from cam_scanner.application.collection_context import CollectionContext
from cam_scanner.cameras.manufacturers.hikvision import HikvisionAdapter
from cam_scanner.cameras.transport import TargetTransportPolicy
from cam_scanner.config.models import EffectiveConfig, TransportProfile
from cam_scanner.config.transport_plan import select_transport
from cam_scanner.domain.models import CameraTarget

_REAL_OPERATION = "GET /ISAPI/System/deviceInfo"
_REALM = "fixture-realm"
_NONCE = "synthetic-nonce"
_ACCOUNTS = {
    "acct-viewer": ("synthetic-viewer-pass", "Viewer"),
    "acct-operator": ("synthetic-operator-pass", "Operator"),
    "acct-admin": ("synthetic-admin-pass", "Administrator"),
}
_ACCOUNT_ORDER = ("acct-viewer", "acct-operator", "acct-admin")
_ALLOWED_ROLES = frozenset({"Operator", "Administrator"})
_DEVICE_INFO = (
    b"<DeviceInfo><manufacturer>FixtureCam</manufacturer>"
    b"<model>Model-F</model><serialNumber>Serial-F</serialNumber>"
    b"</DeviceInfo>"
)


class _AclFixture:
    def __init__(self) -> None:
        self.authenticated_roles: list[str] = []
        self.requests: list[tuple[str, bool]] = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                operation = f"{self.command} {urlsplit(self.path).path}"
                owner.requests.append((operation, "Authorization" in self.headers))
                if operation != _REAL_OPERATION:
                    self._reply(404)
                    return

                role = owner._authenticated_role(self.headers.get("Authorization"))
                if role is None:
                    if "Authorization" not in self.headers:
                        self._reply(401, challenge=True)
                    else:
                        self._reply(401)
                    return

                owner.authenticated_roles.append(role)
                if role not in _ALLOWED_ROLES:
                    self._reply(403)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/xml")
                self.send_header("Content-Length", str(len(_DEVICE_INFO)))
                self.end_headers()
                self.wfile.write(_DEVICE_INFO)

            def _reply(self, status: int, *, challenge: bool = False) -> None:
                self.send_response(status)
                if challenge:
                    self.send_header(
                        "WWW-Authenticate",
                        f'Digest realm="{_REALM}", nonce="{_NONCE}", '
                        'qop="auth", algorithm=MD5',
                    )
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *_args: object) -> None:
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def port(self) -> int:
        return self.server.server_port

    def __enter__(self) -> Self:
        self.thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    @staticmethod
    def _authenticated_role(header: str | None) -> str | None:
        if not header or not header.startswith("Digest "):
            return None
        fields = parse_dict_header(header[7:])
        username = fields.get("username")
        account = _ACCOUNTS.get(username)
        if account is None:
            return None
        password, role = account
        uri = fields.get("uri", "")
        nonce_count = fields.get("nc", "")
        client_nonce = fields.get("cnonce", "")
        qop = fields.get("qop", "")
        if (
            fields.get("realm") != _REALM
            or fields.get("nonce") != _NONCE
            or uri != _REAL_OPERATION.removeprefix("GET ")
            or qop != "auth"
            or not nonce_count
            or not client_nonce
        ):
            return None
        ha1 = hashlib.md5(
            f"{username}:{_REALM}:{password}".encode(), usedforsecurity=False
        ).hexdigest()
        ha2 = hashlib.md5(
            f"GET:{uri}".encode(), usedforsecurity=False
        ).hexdigest()
        expected = hashlib.md5(
            f"{ha1}:{_NONCE}:{nonce_count}:{client_nonce}:{qop}:{ha2}".encode(),
            usedforsecurity=False,
        ).hexdigest()
        if not hmac.compare_digest(fields.get("response", ""), expected):
            return None
        return role


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _exercise_operation(
    fixture: _AclFixture, account_index: int, *, invalid_password: bool = False
) -> tuple[int | None, str | None, str, int, int, tuple[tuple[str, bool], ...]]:
    username = _ACCOUNT_ORDER[account_index]
    password = _ACCOUNTS[username][0]
    if invalid_password:
        password = f"{password}-invalid"
    target = CameraTarget("127.0.0.1", username, password)
    profile_id = "acl-fixture-profile"
    config = EffectiveConfig(transport_profiles=(TransportProfile(
        profile_id,
        ("127.0.0.1",),
        "vendor_hikvision",
        "http",
        fixture.port,
        "NATIVE_DIGEST_EXISTING",
        "ACL-FIXTURE-AUTH",
        True,
    ),))
    selected = select_transport(
        config,
        ["127.0.0.1"],
        {"127.0.0.1": "vendor_hikvision"},
        profile_id,
    )
    context = CollectionContext(
        target, selected, transport_factory=TargetTransportPolicy
    )
    try:
        if context.auth.begin("VENDOR_HIKVISION", "initial"):
            report = HikvisionAdapter().collect_report(target, context=context)
            status = report.attempts[-1].http_status if report.attempts else None
            category = report.attempts[-1].error_category if report.attempts else None
        else:
            status, category = None, "LOGICAL_AUTH_START_REJECTED"
        result = (
            status,
            category,
            context.auth.state,
            context.auth.logical_attempts,
            context.auth.physical_exchanges,
            tuple(fixture.requests),
        )
        return result
    finally:
        context.close()


def test_digest_acl_fixture_authenticates_accounts_for_real_hikvision_operation() -> None:
    cases = (
        (0, 403, "AUTHORIZATION_DENIED", "Viewer", False),
        (1, 200, "AUTH_ACCEPTED", "Operator", False),
        (2, 200, "AUTH_ACCEPTED", "Administrator", False),
        # Known synthetic principal with a deliberately invalid credential.
        (2, 401, "AUTH_REJECTED_FINAL", None, True),
    )

    for index, (account_index, expected_status, expected_state, expected_role, invalid_password) in enumerate(cases):
        with _AclFixture() as fixture:
            status, category, state, logical, physical, requests_seen = _exercise_operation(
                fixture, account_index, invalid_password=invalid_password
            )
            _require(
                status == expected_status,
                f"synthetic ACL row {index} observed HTTP {status!r}, category {category!r}, "
                f"physical exchanges {physical}, fixture requests {len(requests_seen)}",
            )
            _require(state == expected_state, "AuthLedger ended in an unexpected state")
            _require(logical == 1, "logical authentication attempt count mismatch")
            _require(physical == 2, "Digest challenge exchange count mismatch")
            _require(
                requests_seen == ((_REAL_OPERATION, False), (_REAL_OPERATION, True)),
                "fixture observed an unexpected operation or Authorization sequence",
            )
            expected_roles = () if expected_role is None else (expected_role,)
            _require(
                tuple(fixture.authenticated_roles) == expected_roles,
                "fixture did not authenticate the expected account identity",
            )
