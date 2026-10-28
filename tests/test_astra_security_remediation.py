"""Offline regression contracts for the Astra security review findings.

All HTTP behavior is driven by Requests adapter/session doubles. These tests never
open a socket and use only synthetic credential values.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
import requests
from requests.adapters import HTTPAdapter

from cam_scanner.application.collection_context import (
    AuthenticationLedger,
    CollectionContext,
)
from cam_scanner.application.inventory_service import InventoryService
from cam_scanner.application.single_workflow import SingleWorkflow
from cam_scanner.cameras.transport import TargetTransportPolicy
from cam_scanner.config.models import EffectiveConfig, TransportProfile
from cam_scanner.domain.enums import MainMenuChoice
from cam_scanner.domain.models import (
    CameraTarget,
    CollectionAttempt,
    CollectionReport,
)
from cam_scanner.terminal.ui import TerminalUI


def _transport_context() -> CollectionContext:
    return CollectionContext(
        CameraTarget("127.0.0.1", "synthetic-viewer", "synthetic-passphrase"),
        SimpleNamespace(transport_rules=()),
        transport_factory=TargetTransportPolicy,
    )


def _response(
    request: requests.PreparedRequest,
    status: int,
    *,
    challenge: str | None = None,
) -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response.url = request.url
    response.request = request
    response._content = b"{}"
    response.headers["Content-Length"] = "2"
    if challenge is not None:
        response.headers["WWW-Authenticate"] = challenge
    return response


def test_http_200_without_digest_authorization_does_not_accept_authentication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _transport_context()
    sent_headers: list[dict[str, str]] = []

    def synthetic_send(
        _adapter: HTTPAdapter, request: requests.PreparedRequest, **_kwargs: Any
    ) -> requests.Response:
        sent_headers.append(dict(request.headers))
        return _response(request, 200)

    monkeypatch.setattr(HTTPAdapter, "send", synthetic_send)
    try:
        assert context.auth.begin("VENDOR_HIKVISION", "initial")
        response = context.transport.request(
            "vendor_hikvision",
            "GET",
            "https://127.0.0.1/ISAPI/System/deviceInfo",
            source="NATIVE",
            authenticated=True,
            auth=requests.auth.HTTPDigestAuth("synthetic-viewer", "synthetic-passphrase"),
        )

        assert response.status_code == 200
        assert len(sent_headers) == 1
        assert not any(key.casefold() == "authorization" for key in sent_headers[0])
        assert context.auth.state != AuthenticationLedger.AUTH_ACCEPTED
        assert not context.auth.allows_authenticated_request("VENDOR_HIKVISION")
    finally:
        context.close()


def test_digest_challenge_then_200_accepts_only_after_digest_header_was_sent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _transport_context()
    sent_headers: list[dict[str, str]] = []

    def synthetic_send(
        adapter: HTTPAdapter, request: requests.PreparedRequest, **_kwargs: Any
    ) -> requests.Response:
        sent_headers.append(dict(request.headers))
        if len(sent_headers) == 1:
            response = _response(
                request,
                401,
                challenge='Digest realm="offline-fixture", nonce="synthetic-nonce", qop="auth"',
            )
            response.raw = SimpleNamespace(
                headers=SimpleNamespace(getlist=lambda _key: []),
                close=lambda: None,
            )
            response.connection = adapter
            return response
        return _response(request, 200)

    monkeypatch.setattr(HTTPAdapter, "send", synthetic_send)
    try:
        assert context.auth.begin("VENDOR_HIKVISION", "initial")
        response = context.transport.request(
            "vendor_hikvision",
            "GET",
            "https://127.0.0.1/ISAPI/System/deviceInfo",
            source="NATIVE",
            authenticated=True,
            auth=requests.auth.HTTPDigestAuth("synthetic-viewer", "synthetic-passphrase"),
        )

        assert response.status_code == 200
        assert len(sent_headers) == 2
        assert not any(key.casefold() == "authorization" for key in sent_headers[0])
        authorization = next(
            value
            for key, value in sent_headers[1].items()
            if key.casefold() == "authorization"
        )
        assert authorization.startswith("Digest ")
        assert context.auth.state == AuthenticationLedger.AUTH_ACCEPTED
        assert context.auth.allows_authenticated_request("VENDOR_HIKVISION")
    finally:
        context.close()


class _NoSocketCollector:
    def __init__(self) -> None:
        self.calls = 0

    def collect_report(self, _target: CameraTarget, *, context: object = None):
        self.calls += 1
        return CollectionReport()


class _NoSocketSnapshotService:
    def __init__(self) -> None:
        self.calls = 0

    def capture_one(self, *_args: Any, **_kwargs: Any):
        self.calls += 1
        raise AssertionError("snapshot capture must not run for a blocked row")


@pytest.mark.parametrize("model_hint", [None, "WV-S2531", "WV-S2531L-unknown"])
def test_selected_panasonic_http_profile_blocks_row_before_collection_snapshot_or_network(
    model_hint: str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = CameraTarget("192.0.2.30", "offline-user", "offline-secret")
    profile = TransportProfile(
        "panasonic-field",
        (target.ip,),
        "vendor_panasonic",
        "http",
        8080,
        "NATIVE_DIGEST_EXISTING",
        "AUTH-CARD-B",
        True,
    )
    collector = _NoSocketCollector()
    snapshots = _NoSocketSnapshotService()
    service = InventoryService(
        collector,
        config=EffectiveConfig(transport_profiles=(profile,)),
    )
    prepared_rows: list[tuple[object, bool, dict[str, str | None]]] = []
    original_prepare = service.prepare_transport_for_row

    def capture_prepared_row(*args: Any, **kwargs: Any):
        prepared = original_prepare(*args, **kwargs)
        prepared_rows.append(prepared)
        return prepared

    service.prepare_transport_for_row = capture_prepared_row  # type: ignore[method-assign]
    sent_requests: list[str] = []

    def reject_network_send(
        _adapter: HTTPAdapter,
        request: requests.PreparedRequest,
        **_kwargs: Any,
    ) -> requests.Response:
        sent_requests.append(request.url or "")
        raise AssertionError("network transport must not run for a blocked row")

    monkeypatch.setattr(HTTPAdapter, "send", reject_network_send)

    class _UI:
        report: CollectionReport | None = None

        def prompt_camera_target(self) -> CameraTarget:
            return target

        def prompt_manufacturer_hint(self) -> str:
            return "Panasonic"

        def prompt_model_hint(self) -> str | None:
            return model_hint

        def prompt_transport_selection(self, options) -> str:
            option = next(item for item in options if item.selection_id == profile.id)
            assert not option.available
            return profile.id

        def render_report(self, report: CollectionReport, **_kwargs: Any) -> None:
            self.report = report

        def post_query_menu(self) -> MainMenuChoice:
            return MainMenuChoice.EXIT

    ui = _UI()

    result = SingleWorkflow(ui, service, snapshots).run()

    assert result is MainMenuChoice.EXIT
    assert len(prepared_rows) == 1
    _effective_config, blocked, metadata = prepared_rows[0]
    assert blocked is True
    assert metadata["policy_id"] == profile.id
    assert collector.calls == 0
    assert snapshots.calls == 0
    assert sent_requests == []
    assert ui.report is not None
    assert any(
        attempt.operation == "select_transport_policy"
        and attempt.outcome == "SKIPPED"
        for attempt in ui.report.attempts
    )


def test_credentials_equal_to_transport_ids_are_removed_from_report_and_terminal() -> None:
    username = "line-owner-47"
    password = "synthetic-cobalt-83"
    target = CameraTarget("192.0.2.40", username, password)
    attempt = CollectionAttempt(
        stage="CONNECT",
        operation="select_transport_policy",
        outcome="SKIPPED",
        metadata={
            "policy_id": username,
            "authorization_ref": password,
            "auth_mode": "NATIVE_DIGEST_EXISTING",
        },
    )
    report = CollectionReport().with_attempt(attempt).validated_for_target(
        (target.username, target.password)
    )
    output: list[str] = []
    TerminalUI(output_fn=output.append).render_report(
        report,
        ip=target.ip,
        duration=0.0,
    )

    assert username not in repr(report.attempts[0].metadata)
    assert password not in repr(report.attempts[0].metadata)
    assert username not in "\n".join(output)
    assert password not in "\n".join(output)


def test_credentials_equal_to_transport_provenance_ids_are_discarded() -> None:
    username = "row-credential-owner"
    password = "row-credential-value"

    class _Policy:
        def policy_metadata(self, _component: str, _url: str) -> dict[str, str]:
            return {
                "policy_id": username,
                "authorization_ref": password,
                "auth_mode": "NATIVE_DIGEST_EXISTING",
            }

    from cam_scanner.cameras.manufacturers._http_utils import transport_provenance

    _protocol, metadata = transport_provenance(
        SimpleNamespace(
            target=CameraTarget("192.0.2.41", username, password),
            transport=_Policy(),
        ),
        "vendor_panasonic",
        "https://192.0.2.41/cgi-bin/getinfo?FILE=1",
        auth_mode="NATIVE_DIGEST_EXISTING",
    )

    assert username not in repr(metadata)
    assert password not in repr(metadata)
