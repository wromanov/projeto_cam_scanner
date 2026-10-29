"""Axis anonymous plan stops after unsafe replies, interruption, and TLS failure."""
from __future__ import annotations

import pytest
import requests

from cam_scanner.application.collection_context import CollectionContext, CollectionDeadlineExceeded
from cam_scanner.application.inventory_service import InventoryService
from cam_scanner.application.single_workflow import SingleWorkflow
from cam_scanner.cameras.manufacturers.axis import AxisAdapter
from cam_scanner.cameras.registry import build_default_registry
from cam_scanner.cameras.strategy import VendorFirstCollector
from cam_scanner.cameras.transport import TargetTransportPolicy
from cam_scanner.config.models import EffectiveConfig, TransportRule
from cam_scanner.domain.enums import MainMenuChoice
from cam_scanner.domain.models import CollectionReport
from tests.test_astra_gpn_joint_integration import _HttpsFixture, _NoMedia, _SingleUI
from tests.test_astra_p0_axis_gap_closure import (
    _PROPERTIES,
    _SUPPORTED,
    _VERSIONS,
    _assert_public_requests,
    _axis_fixture,
    _context,
    _Reply,
    _target,
)


def _observe_closes(monkeypatch: pytest.MonkeyPatch) -> tuple[list[int], list[int]]:
    responses: list[int] = []
    sessions: list[int] = []
    response_close = requests.Response.close
    session_close = requests.Session.close

    def close_response(response):
        responses.append(id(response))
        return response_close(response)

    def close_session(session):
        sessions.append(id(session))
        return session_close(session)

    monkeypatch.setattr(requests.Response, "close", close_response)
    monkeypatch.setattr(requests.Session, "close", close_session)
    return responses, sessions


def test_axis_oversized_first_body_closes_resources_without_second_post(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses, sessions = _observe_closes(monkeypatch)
    with _axis_fixture((_Reply(200, b"x" * (64 * 1024 + 1)), _Reply(200, _PROPERTIES))) as (
        server, observed,
    ):
        target = _target()
        context = _context(server, target)
        try:
            report = AxisAdapter().collect_report(target, context=context)
            assert report.attempts[-1].error_category == "INVALID_RESPONSE"
            assert [item.operation for item in observed] == [_VERSIONS]
            assert context.auth.logical_attempts == 0
            assert context.auth.physical_exchanges == 1
            _assert_public_requests(observed)
        finally:
            assert context.close()
    assert responses and sessions


@pytest.mark.parametrize("interruption", ["deadline", "cancel"])
def test_axis_interruption_after_versions_closes_before_second_post(
    monkeypatch: pytest.MonkeyPatch, interruption: str,
) -> None:
    responses, sessions = _observe_closes(monkeypatch)
    with _axis_fixture((_Reply(200, _SUPPORTED), _Reply(200, _PROPERTIES))) as (
        server, observed,
    ):
        target = _target()
        preflight_context = _context(server, target)
        config = preflight_context.config
        assert preflight_context.close()
        now = [100.0]
        context = CollectionContext(
            target, config, transport_factory=TargetTransportPolicy, clock=lambda: now[0],
        )
        observed_close = requests.Response.close

        def interrupt_after_first_response(response):
            result = observed_close(response)
            if interruption == "deadline":
                now[0] = context.budget.deadline + 1.0
            else:
                context.cancel_event.set()
            return result

        monkeypatch.setattr(requests.Response, "close", interrupt_after_first_response)
        try:
            report = AxisAdapter().collect_report(target, context=context)
            attempt = report.attempts[-1]
            if interruption == "deadline":
                assert attempt.error_category == "DEADLINE_EXCEEDED"
            else:
                assert attempt.outcome == "CANCELLED"
            assert [item.operation for item in observed] == [_VERSIONS]
            assert context.auth.logical_attempts == 0
            assert context.auth.physical_exchanges == 1
            _assert_public_requests(observed)
        finally:
            assert context.close()
    assert responses and sessions


def test_axis_invalid_tls_closes_before_http_request_and_never_replays(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _responses, sessions = _observe_closes(monkeypatch)
    with _HttpsFixture("partial") as server:
        target = _target()
        config = EffectiveConfig(transport_rules=(
            TransportRule("127.0.0.1", "vendor_axis", "https", None, server.port),
        ))
        context = CollectionContext(target, config, transport_factory=TargetTransportPolicy)
        try:
            report = AxisAdapter().collect_report(target, context=context)
            assert report.attempts[-1].error_category == "TLS_ERROR"
            assert context.tls_failed
            assert context.auth.logical_attempts == 0
            assert context.auth.physical_exchanges == 1
            assert server.requests == []
        finally:
            assert context.close()
    assert sessions


@pytest.mark.parametrize("failure_operation", ["versions", "properties"])
def test_axis_documented_2001_is_terminal_in_same_ledger(
    failure_operation: str,
) -> None:
    denial = _Reply(200, b'{"error":{"code":2001,"message":"denied"}}')
    replies = (denial,) if failure_operation == "versions" else (_Reply(200, _SUPPORTED), denial)
    expected_exchanges = 1 if failure_operation == "versions" else 2
    with _axis_fixture(replies) as (server, observed):
        target = _target()
        context = _context(server, target)
        try:
            report = AxisAdapter().collect_report(target, context=context)
            assert report.attempts[-1].error_category == "AUTHORIZATION_DENIED"
            assert context.auth.state == context.auth.AUTHORIZATION_DENIED
            assert context.auth.logical_attempts == 0
            assert context.auth.physical_exchanges == expected_exchanges
            assert len(observed) == expected_exchanges
            _assert_public_requests(observed)
            assert not context.auth.begin("ONVIF", "initial")
            assert context.auth.logical_attempts == 0
        finally:
            assert context.close()


@pytest.mark.parametrize("failure", ["oversized", "adapter_deadline", "before_adapter_deadline"])
def test_single_axis_failure_does_not_fall_back_to_onvif(
    monkeypatch: pytest.MonkeyPatch, failure: str,
) -> None:
    """Exercise real SINGLE, inventory, strategy and Axis with a bounded fixture."""
    body = b"x" * (64 * 1024 + 1) if failure == "oversized" else _SUPPORTED
    onvif_calls: list[str] = []
    discovery_calls: list[str] = []
    contexts: list[CollectionContext] = []

    class OnvifSpy:
        def collect_report(self, target, *, context=None):
            onvif_calls.append("called")
            return CollectionReport()

    class DiscoverySpy:
        def discover(self, target, *, context=None):
            discovery_calls.append("called")

    class CapturingService(InventoryService):
        def create_context(self, target, **kwargs):
            context = super().create_context(target, **kwargs)
            contexts.append(context)
            if failure == "before_adapter_deadline":
                original_check = context.check

                def check(source):
                    if source == "NATIVE":
                        raise CollectionDeadlineExceeded("synthetic pre-adapter deadline")
                    return original_check(source)

                monkeypatch.setattr(context, "check", check)
            return context

    class AxisUI(_SingleUI):
        def prompt_manufacturer_hint(self) -> str:
            return "Axis"

        def prompt_transport_selection(self, _options) -> str:
            return "axis-public-loopback"

    with _axis_fixture((_Reply(200, body), _Reply(200, _PROPERTIES))) as (server, observed):
        preflight = _context(server, _target())
        config = preflight.config
        assert preflight.close()
        collector = VendorFirstCollector(
            onvif_collector=OnvifSpy(), registry=build_default_registry(), discoverer=DiscoverySpy(),
        )
        service = CapturingService(collector, config=config)
        if failure == "adapter_deadline":
            original_close = requests.Response.close

            def expire_budget(response):
                result = original_close(response)
                contexts[0].budget.charge("NATIVE", 30.0)
                return result

            monkeypatch.setattr(requests.Response, "close", expire_budget)
        ui = AxisUI(None, manufacturer="Axis")
        assert SingleWorkflow(ui, service, _NoMedia()).run() is MainMenuChoice.EXIT

    assert len(contexts) == 1
    context = contexts[0]
    assert not discovery_calls and not onvif_calls
    assert len(observed) == (0 if failure == "before_adapter_deadline" else 1)
    assert context.auth.logical_attempts == 0
    assert context.auth.physical_exchanges == len(observed)
    _assert_public_requests(observed)
    expected = "INVALID_RESPONSE" if failure == "oversized" else "DEADLINE_EXCEEDED"
    assert any(attempt.error_category == expected for attempt in ui.report.attempts)
