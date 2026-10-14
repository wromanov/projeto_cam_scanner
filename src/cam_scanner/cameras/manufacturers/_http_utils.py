"""Small deadline helpers for bounded vendor HTTP reads."""
from __future__ import annotations

import time
from collections.abc import Iterable


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
    chunks: Iterable[bytes], limit: int, started: float, budget: float
) -> bytes:
    body = bytearray()
    for chunk in chunks:
        remaining_budget(started, budget)
        body.extend(chunk)
        if len(body) > limit:
            raise ValueError("response too large")
    remaining_budget(started, budget)
    return bytes(body)
