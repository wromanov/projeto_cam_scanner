"""Small deadline helpers for bounded vendor HTTP reads."""
from __future__ import annotations

import time
from collections.abc import Iterable
from contextlib import nullcontext
from typing import Any

import requests


class DeadlineExceeded(Exception):
    """A logical vendor operation exhausted its cumulative time budget."""


def remaining_budget(started: float, budget: float) -> float:
    remaining = budget - (time.monotonic() - started)
    if remaining <= 0:
        raise DeadlineExceeded
    return remaining


def bounded_timeout(timeout: tuple[float, float], started: float, budget: float) -> tuple[float, float]:
    remaining = remaining_budget(started, budget)
    return min(timeout[0], remaining), min(timeout[1], remaining)


def read_limited_until(
    chunks: Iterable[bytes], limit: int, started: float, budget: float,
    *, context: Any = None, source: str = "NATIVE",
) -> bytes:
    body = bytearray()
    for chunk in chunks:
        if context is not None:
            context.check(source)
        remaining_budget(started, budget)
        body.extend(chunk)
        if len(body) > limit:
            raise ValueError("response too large")
    remaining_budget(started, budget)
    return bytes(body)


class _ContextVendorSession:
    def __init__(self, context: Any, component: str) -> None:
        self.context = context
        self.component = component
        self.trust_env = False

    def get(self, url: str, **options: Any) -> Any:
        return self.context.transport.request(self.component, "GET", url,
                                              source="NATIVE", **options)

    def post(self, url: str, **options: Any) -> Any:
        return self.context.transport.request(self.component, "POST", url,
                                              source="NATIVE", **options)


def managed_vendor_session(context: Any, component: str, session_factory: Any) -> Any:
    """Use the shared policy; direct injected fake sessions remain test-compatible."""
    if context is not None:
        context.check("NATIVE")
        return nullcontext(_ContextVendorSession(context, component))
    if session_factory is requests.Session:
        raise ValueError("collection context required for network I/O")
    return session_factory()
