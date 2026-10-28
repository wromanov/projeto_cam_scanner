"""Focused cross-invariant evidence for ASTRA evidence completion 03.

All HTTP requests are limited to a synthetic loopback fixture.
"""
from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Self

import pytest

from cam_scanner.application.collection_context import CollectionContext
from cam_scanner.cameras.manufacturers.hikvision import HikvisionAdapter
from cam_scanner.cameras.transport import TargetTransportPolicy
from cam_scanner.config.models import EffectiveConfig, TransportProfile
from cam_scanner.config.transport_plan import select_transport
from cam_scanner.domain.models import CameraTarget, CollectionReport, EvidenceRecord, ModelHint


class _ChallengeFixture:
    def __init__(self, challenge: str, final_status: int) -> None:
        self.challenge = challenge
        self.final_status = final_status
        self.requests: list[bool] = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                authenticated = "Authorization" in self.headers
                owner.requests.append(authenticated)
                status = owner.final_status if authenticated else 401
                self.send_response(status)
                if not authenticated:
                    self.send_header("WWW-Authenticate", owner.challenge)
                self.send_header("Connection", "close")
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


@pytest.mark.parametrize(
    ("challenge", "final_status", "category", "ledger_state", "physical", "sequence"),
    [
        (
            'Basic realm="fixture"',
            401,
            "AUTH_MECHANISM_UNSUPPORTED",
            "AUTH_REJECTED_FINAL",
            1,
            [False],
        ),
        (
            (
                'Digest realm="fixture", nonce="synthetic-nonce", '
                'qop="auth", algorithm=SHA-256'
            ),
            401,
            "AUTH_MECHANISM_UNSUPPORTED",
            "AUTH_REJECTED_FINAL",
            1,
            [False],
        ),
        (
            (
                'Digest realm="fixture", nonce="synthetic-nonce", '
                'qop="auth", algorithm=MD5'
            ),
            401,
            "AUTH_REJECTED",
            "AUTH_REJECTED_FINAL",
            2,
            [False, True],
        ),
        (
            (
                'Digest realm="fixture", nonce="synthetic-nonce", '
                'qop="auth", algorithm=MD5'
            ),
            403,
            "AUTHORIZATION_DENIED",
            "AUTHORIZATION_DENIED",
            2,
            [False, True],
        ),
    ],
)
def test_auth_challenge_matrix_counts_exchanges_and_blocks_later_families(
    challenge: str,
    final_status: int,
    category: str,
    ledger_state: str,
    physical: int,
    sequence: list[bool],
) -> None:
    with _ChallengeFixture(challenge, final_status) as fixture:
        target = CameraTarget(
            "127.0.0.1", "evidence-user-sentinel", "evidence-password-sentinel",
        )
        profile = TransportProfile(
            "auth-fixture",
            ("127.0.0.1",),
            "vendor_hikvision",
            "http",
            fixture.port,
            "NATIVE_DIGEST_EXISTING",
            "AUTH-EVIDENCE-03",
            True,
        )
        config = select_transport(
            EffectiveConfig(transport_profiles=(profile,)),
            ["127.0.0.1"],
            {"127.0.0.1": "vendor_hikvision"},
            profile.id,
        )
        context = CollectionContext(
            target, config, transport_factory=TargetTransportPolicy,
        )
        try:
            assert context.auth.begin("VENDOR_HIKVISION", "initial")
            report = HikvisionAdapter().collect_report(target, context=context)

            assert len(report.attempts) == 1
            assert report.attempts[0].http_status == final_status
            assert report.attempts[0].error_category == category
            assert fixture.requests == sequence
            assert context.auth.logical_attempts == 1
            assert context.auth.physical_exchanges == physical
            assert context.auth.state == ledger_state
            assert not context.auth.begin(
                "ONVIF",
                "missing_identity",
                missing_identity_fields=("manufacturer",),
            )
            assert not context.auth.begin(
                "VENDOR_PANASONIC",
                "missing_identity",
                missing_identity_fields=("manufacturer",),
            )
            assert context.auth.state == ledger_state
            assert "evidence-user-sentinel" not in repr(report)
            assert "evidence-password-sentinel" not in repr(report)
        finally:
            context.close()


def test_model_hint_mismatch_preserves_observed_evidence_in_both_merge_orders() -> None:
    hint_only = CollectionReport().with_model_hint(ModelHint("WV-S2531L"))
    observed_only = CollectionReport().with_evidence(
        EvidenceRecord(
            field="model",
            value="WV-S2531M",
            source="VENDOR",
            protocol="HTTPS",
            operation="GET /cgi-bin/getinfo",
        ),
        EvidenceRecord(
            field="serial",
            value="SERIAL-FIXTURE",
            source="VENDOR",
            protocol="HTTPS",
            operation="GET /cgi-bin/getinfo",
        ),
        EvidenceRecord(
            field="firmware",
            value="9.99",
            source="VENDOR",
            protocol="HTTPS",
            operation="GET /cgi-bin/getinfo",
        ),
    )

    for merged in (hint_only.merged(observed_only), observed_only.merged(hint_only)):
        assert merged.model_hint == ModelHint("WV-S2531L")
        assert merged.model_mismatch
        assert merged.value_for("model") == "WV-S2531M"
        result = merged.to_camera_result("127.0.0.1")
        assert result.model == "WV-S2531M"
        assert result.serial == "SERIAL-FIXTURE"
        assert result.firmware == "9.99"
