"""Small deadline helpers for bounded vendor HTTP reads."""
from __future__ import annotations

import time
from collections.abc import Iterable, Mapping
from contextlib import nullcontext
from typing import Any
from urllib.parse import urlsplit

import requests

_AUTH_MODES = frozenset({
    "NONE", "EXISTING", "PUBLIC_NONE", "NATIVE_DIGEST_EXISTING",
})


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


def transport_provenance(
    context: Any, component: str, url: str, *, auth_mode: str
) -> tuple[str | None, dict[str, str]]:
    """Return the actual HTTP scheme and closed, sanitized policy metadata."""
    try:
        scheme = urlsplit(url).scheme.casefold()
    except (TypeError, ValueError):
        return None, {}
    if scheme not in {"http", "https"}:
        return None, {}

    fallback_policy = "HTTPS_DEFAULT" if scheme == "https" else "LEGACY_EXACT"
    fallback_auth = auth_mode if auth_mode in _AUTH_MODES else "EXISTING"
    raw: object = None
    transport = getattr(context, "transport", None) if context is not None else None
    policy_method = getattr(transport, "policy_metadata", None)
    if callable(policy_method):
        try:
            raw = policy_method(component, url)
        except Exception:  # noqa: BLE001 - diagnostic provenance must remain non-fatal.
            raw = None
    source = raw if isinstance(raw, Mapping) else {}

    policy_id = source.get("policy_id")
    if not _safe_transport_id(policy_id):
        policy_id = fallback_policy
    selected_auth = source.get("auth_mode")
    if type(selected_auth) is not str or selected_auth not in _AUTH_MODES:
        selected_auth = fallback_auth
    metadata = {
        "policy_id": policy_id,
        "auth_mode": selected_auth,
        "scheme": scheme,
    }
    authorization_ref = source.get("authorization_ref")
    if _safe_transport_id(authorization_ref):
        metadata["authorization_ref"] = authorization_ref
    target = getattr(context, "target", None) if context is not None else None
    sensitive_values = tuple(
        value for value in (
            getattr(target, "username", None),
            getattr(target, "password", None),
        )
        if isinstance(value, str) and value
    )
    for key, value in tuple(metadata.items()):
        if isinstance(value, str) and any(
            secret.casefold() in value.casefold() for secret in sensitive_values
        ):
            metadata.pop(key)
    return scheme.upper(), metadata


def _safe_transport_id(value: object) -> bool:
    if (type(value) is not str or not 1 <= len(value) <= 64
            or not all(char.isascii() and (char.isalnum() or char in "_-") for char in value)):
        return False
    lowered = value.casefold()
    return not any(marker in lowered for marker in (
        "password", "passwd", "secret", "token", "credential", "username",
    ))
