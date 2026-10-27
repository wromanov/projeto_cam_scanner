from __future__ import annotations

from types import SimpleNamespace

import pytest

from cam_scanner.application.collection_context import (
    AuthenticationLedger,
    CollectionBudget,
    CollectionCancelled,
    CollectionContext,
    CollectionDeadlineExceeded,
)
from cam_scanner.domain.models import CameraTarget, CollectionReport


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _config(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "connect_timeout_seconds": 3,
        "request_timeout_seconds": 7,
        "onvif_budget_seconds": 15,
        "manufacturer_budget_seconds": 10,
        "camera_soft_deadline_seconds": 45,
        "snapshot_http_timeout_seconds": 10,
        "rtsp_open_timeout_seconds": 8,
        "rtsp_first_frame_timeout_seconds": 5,
        "max_retries": 0,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _target(ip: str = "192.0.2.15") -> CameraTarget:
    return CameraTarget(ip=ip, username="camera-user", password="secret")


def test_source_and_camera_deadlines_are_monotonic_and_cumulative() -> None:
    clock = FakeClock()
    budget = CollectionBudget(_config(), started_at=clock(), clock=clock)

    assert budget.request_timeout("ONVIF", 3, 7) == (3.0, 7.0)
    budget.charge("ONVIF", 8)
    assert budget.remaining("ONVIF") == 7

    clock.advance(40)
    assert budget.remaining("ONVIF") == 5
    clock.advance(5)
    assert budget.remaining("ONVIF") == 0
    with pytest.raises(CollectionDeadlineExceeded):
        budget.request_timeout("ONVIF", 3, 7)


def test_measure_charges_source_budget_even_when_operation_raises() -> None:
    clock = FakeClock()
    budget = CollectionBudget(_config(), started_at=clock(), clock=clock)

    with pytest.raises(RuntimeError), budget.measure("NATIVE"):
        clock.advance(2.5)
        raise RuntimeError("synthetic failure")

    assert budget.remaining("NATIVE") == 7.5


def test_retries_default_to_zero_and_never_exceed_one_configured_retry() -> None:
    clock = FakeClock()
    default_budget = CollectionBudget(_config(), started_at=clock(), clock=clock)
    assert not default_budget.retry_allowed("NATIVE", eligible=True)

    one_retry = CollectionBudget(
        _config(max_retries=1), started_at=clock(), clock=clock
    )
    assert one_retry.retry_allowed("NATIVE", eligible=True)
    one_retry.record_retry("NATIVE")
    assert not one_retry.retry_allowed("NATIVE", eligible=True)
    assert not one_retry.retry_allowed("NATIVE", eligible=False)


def test_auth_ledger_counts_digest_challenge_physically_but_not_logically() -> None:
    ledger = AuthenticationLedger()
    assert ledger.begin("ONVIF", "PRIMARY")
    ledger.record_physical_exchange()
    ledger.observe_http(401, "ONVIF", authenticated=False, challenge=True)
    ledger.record_physical_exchange()

    assert ledger.logical_attempts == 1
    assert ledger.physical_exchanges == 2
    assert ledger.state == ledger.AUTH_NEGOTIATION
    assert not ledger.allows_authenticated_request("ONVIF")

    ledger.observe_http(200, "ONVIF", authenticated=True)
    assert ledger.allows_authenticated_request("ONVIF")
    ledger.observe_http(401, "ONVIF", authenticated=True)
    assert ledger.state == ledger.AUTH_REJECTED_FINAL
    assert not ledger.begin("VENDOR:AXIS", "MISSING_IDENTITY", missing_identity_fields=("serial",))


def test_anonymous_401_does_not_block_the_planned_primary_authentication() -> None:
    ledger = AuthenticationLedger()
    ledger.observe_http(401, "ONVIF", authenticated=False)

    assert ledger.state == ledger.AUTH_SCOPE_UNKNOWN
    assert ledger.begin("ONVIF", "PRIMARY")


def test_second_logical_attempt_requires_missing_identity_and_single_vendor_family() -> None:
    ledger = AuthenticationLedger()
    assert ledger.begin("ONVIF", "PRIMARY")
    assert not ledger.begin("VENDOR:AXIS", "PRIMARY")
    assert ledger.begin(
        "VENDOR:AXIS", "MISSING_IDENTITY", missing_identity_fields=("serial",)
    )
    assert not ledger.begin(
        "VENDOR:DAHUA", "MISSING_IDENTITY", missing_identity_fields=("model",)
    )
    assert ledger.logical_attempts == 2


def test_soap_not_authorized_does_not_authorize_an_authentication_retry() -> None:
    ledger = AuthenticationLedger()
    ledger.observe_soap("ter:NotAuthorized", authenticated=False)

    assert ledger.state == ledger.AUTH_SCOPE_UNKNOWN
    # The planned collection login remains available; the SOAP fault cannot
    # justify a second, diagnostic login attempt.
    assert not ledger.begin(
        "VENDOR:AXIS", "MISSING_IDENTITY", missing_identity_fields=("serial",)
    )
    assert ledger.begin("ONVIF", "PRIMARY")
    assert ledger.allows_authenticated_attempt("ONVIF")
    assert not ledger.begin(
        "VENDOR:AXIS", "MISSING_IDENTITY", missing_identity_fields=("serial",)
    )


def test_authenticated_soap_not_authorized_preserves_cause_and_blocks_scope() -> None:
    ledger = AuthenticationLedger()
    assert ledger.begin("ONVIF", "PRIMARY")
    ledger.observe_http(200, "ONVIF", authenticated=True)

    ledger.observe_soap("ter:NotAuthorized", authenticated=True)

    assert ledger.state == ledger.AUTH_ACCEPTED
    assert ledger.soap_access_blocked
    assert not ledger.allows_authenticated_request("ONVIF")
    assert not ledger.allows_authenticated_attempt("ONVIF")
    assert not ledger.begin("ONVIF", "PRIMARY")


def test_context_shares_cancel_report_and_closes_registered_resources_once() -> None:
    clock = FakeClock()
    config = _config()
    context = CollectionContext(_target(), config, clock=clock)
    closed: list[int] = []

    class Resource:
        def __init__(self, marker: int) -> None:
            self.marker = marker

        def close(self) -> None:
            closed.append(self.marker)

    context.register(Resource(1))
    context.register(Resource(2))
    assert context.merge(CollectionReport()) == context.report
    assert context.request_timeout("ONVIF") == (3.0, 7.0)
    assert context.close()
    assert context.close()
    assert closed == [2, 1]

    context.cancel_event.set()
    with pytest.raises(CollectionCancelled):
        context.check("ONVIF")


def test_snapshot_eligibility_requires_accepted_auth_and_budget_not_result_status() -> None:
    clock = FakeClock()
    context = CollectionContext(_target(), _config(), clock=clock)
    assert not context.snapshot_eligible("ONVIF")

    assert context.auth.begin("ONVIF", "PRIMARY")
    context.auth.observe_http(200, "ONVIF", authenticated=True)
    assert context.snapshot_eligible("ONVIF")

    context.cancel_event.set()
    assert not context.snapshot_eligible("ONVIF")
