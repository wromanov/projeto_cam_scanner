"""Per-camera execution state shared from pre-auth discovery through cleanup."""
from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from math import isfinite
from typing import Any, Protocol

from cam_scanner.domain.models import CameraTarget, CollectionReport


class TransportPolicy(Protocol):
    """Target-bound network policy implemented by ``cameras.transport``."""

    def authorize(self, component: str, url: str) -> Any: ...

    def request(
        self, component: str, method: str, url: str, *, source: str, **options: Any
    ) -> Any: ...


class CollectionCancelled(RuntimeError):
    """Raised at a cooperative checkpoint after cancellation was requested."""


class CollectionDeadlineExceeded(TimeoutError):
    """Raised when a camera or source budget has no time left for another I/O."""


class AuthenticationLedger:
    """Authentication decisions scoped to one target row and one collection."""

    AUTH_SCOPE_UNKNOWN = "AUTH_SCOPE_UNKNOWN"
    AUTH_NEGOTIATION = "AUTH_NEGOTIATION"
    AUTH_ACCEPTED = "AUTH_ACCEPTED"
    AUTH_REJECTED_FINAL = "AUTH_REJECTED_FINAL"
    AUTHORIZATION_DENIED = "AUTHORIZATION_DENIED"

    _IDENTITY_FIELDS = frozenset({"manufacturer", "model", "serial"})
    _ONVIF_FAMILIES = frozenset({"ONVIF", "GENERIC_ONVIF", "ONVIF_PREAUTH"})

    def __init__(self) -> None:
        self._state = self.AUTH_SCOPE_UNKNOWN
        self._logical_attempts = 0
        self._vendor_family: str | None = None
        self._families_started: set[str] = set()
        self._accepted_families: set[str] = set()
        self._physical_exchanges = 0
        self._soap_auth_retry_blocked = False
        self._lock = threading.RLock()

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    @property
    def logical_attempts(self) -> int:
        with self._lock:
            return self._logical_attempts

    @property
    def physical_exchanges(self) -> int:
        with self._lock:
            return self._physical_exchanges

    def begin(
        self,
        family: str,
        reason: str,
        *,
        missing_identity_fields: tuple[str, ...] | frozenset[str] = (),
    ) -> bool:
        """Start one logical authenticated attempt, never a Digest challenge replay."""
        normalized_family = self._normalize_family(family)
        missing = frozenset(missing_identity_fields) & self._IDENTITY_FIELDS
        with self._lock:
            if self._state in {self.AUTH_REJECTED_FINAL, self.AUTHORIZATION_DENIED}:
                return False
            if self._soap_auth_retry_blocked:
                return False
            if normalized_family not in self._ONVIF_FAMILIES:
                if self._vendor_family not in {None, normalized_family}:
                    return False
                self._vendor_family = normalized_family
            if normalized_family in self._families_started:
                return False
            if self._logical_attempts >= 2:
                return False
            if self._logical_attempts == 1 and (
                not missing or reason.casefold() not in {"missing_identity", "identity_incomplete"}
            ):
                return False
            self._logical_attempts += 1
            self._families_started.add(normalized_family)
            self._state = self.AUTH_NEGOTIATION
            return True

    def observe_http(
        self,
        status: int,
        family: str,
        *,
        authenticated: bool,
        challenge: bool = False,
    ) -> None:
        """Record an HTTP auth transition; challenge exchanges do not start logins."""
        if type(status) is not int:
            return
        normalized_family = self._normalize_family(family)
        with self._lock:
            if self._state in {self.AUTH_REJECTED_FINAL, self.AUTHORIZATION_DENIED}:
                return
            if 200 <= status < 300 and authenticated:
                self._state = self.AUTH_ACCEPTED
                self._accepted_families.add(normalized_family)
            elif status == 401:
                self._state = self.AUTH_NEGOTIATION if challenge else (
                    self.AUTH_REJECTED_FINAL if authenticated else self._state
                )
            elif status == 403:
                self._state = self.AUTHORIZATION_DENIED

    def observe_soap(self, code: str | None, *, authenticated: bool = False) -> None:
        """A SOAP NotAuthorized fault never authorizes a diagnostic login retry."""
        if not isinstance(code, str) or "notauthorized" not in code.replace("_", "").casefold():
            return
        with self._lock:
            if self._state in {self.AUTH_REJECTED_FINAL, self.AUTHORIZATION_DENIED}:
                return
            self._soap_auth_retry_blocked = True
            if authenticated:
                self._state = self.AUTHORIZATION_DENIED

    def record_physical_exchange(self, count: int = 1) -> None:
        if type(count) is not int or count < 0:
            raise ValueError("physical exchange count must be a non-negative integer")
        with self._lock:
            self._physical_exchanges += count

    def allows_authenticated_request(self, family: str) -> bool:
        normalized_family = self._normalize_family(family)
        with self._lock:
            return (
                self._state == self.AUTH_ACCEPTED
                and normalized_family in self._accepted_families
            )

    @staticmethod
    def _normalize_family(family: str) -> str:
        if not isinstance(family, str) or not family.strip():
            raise ValueError("authentication family must be non-empty")
        return family.strip().upper()


class CollectionBudget:
    """Monotonic per-camera deadline plus cumulative per-source time budgets."""

    _SOURCE_CONFIG = {
        "ONVIF": ("onvif_budget_seconds", 15.0),
        "NATIVE": ("manufacturer_budget_seconds", 10.0),
        "SNAPSHOT_HTTP": ("snapshot_http_timeout_seconds", 10.0),
        "RTSP_OPEN": ("rtsp_open_timeout_seconds", 8.0),
        "RTSP_FRAME": ("rtsp_first_frame_timeout_seconds", 5.0),
    }

    def __init__(
        self,
        config: object,
        *,
        started_at: float,
        clock: Callable[[], float],
    ) -> None:
        self._config = config
        self._started_at = started_at
        self._clock = clock
        self._camera_limit = self._positive_config("camera_soft_deadline_seconds", 45.0)
        self._source_limits = {
            name: self._positive_config(attribute, default)
            for name, (attribute, default) in self._SOURCE_CONFIG.items()
        }
        self._source_spent = dict.fromkeys(self._source_limits, 0.0)
        self._retry_counts = dict.fromkeys(self._source_limits, 0)
        self._lock = threading.RLock()

    @property
    def started_at(self) -> float:
        return self._started_at

    @property
    def deadline(self) -> float:
        return self._started_at + self._camera_limit

    def remaining(self, source: str) -> float:
        key = self._source(source)
        with self._lock:
            source_remaining = max(0.0, self._source_limits[key] - self._source_spent[key])
        camera_remaining = max(0.0, self.deadline - self._clock())
        return min(source_remaining, camera_remaining)

    def request_timeout(
        self, source: str, connect_cap: float, read_cap: float
    ) -> tuple[float, float]:
        remaining = self.remaining(source)
        if remaining <= 0:
            raise CollectionDeadlineExceeded("budget esgotado antes de nova operação")
        connect = self._positive_number(connect_cap, "connect timeout")
        read = self._positive_number(read_cap, "read timeout")
        return min(connect, remaining), min(read, remaining)

    def charge(self, source: str, elapsed: float) -> None:
        key = self._source(source)
        if type(elapsed) not in {float, int} or not isfinite(float(elapsed)) or elapsed < 0:
            raise ValueError("elapsed time must be finite and non-negative")
        with self._lock:
            self._source_spent[key] += float(elapsed)

    @contextmanager
    def measure(self, source: str) -> Iterator[None]:
        self.remaining(source)  # Validate source and fail before beginning I/O.
        started = self._clock()
        try:
            yield
        finally:
            self.charge(source, max(0.0, self._clock() - started))

    def retry_allowed(self, source: str, *, eligible: bool) -> bool:
        key = self._source(source)
        max_retries = getattr(self._config, "max_retries", 0)
        if type(max_retries) is not int or max_retries < 0:
            return False
        with self._lock:
            return (
                eligible
                and self._retry_counts[key] < max_retries
                and self.remaining(key) > 0
            )

    def record_retry(self, source: str) -> None:
        key = self._source(source)
        with self._lock:
            if self._retry_counts[key] >= getattr(self._config, "max_retries", 0):
                raise ValueError("retry limit exceeded")
            self._retry_counts[key] += 1

    def _positive_config(self, attribute: str, default: float) -> float:
        return self._positive_number(getattr(self._config, attribute, default), attribute)

    @classmethod
    def _source(cls, source: str) -> str:
        key = source.strip().upper() if isinstance(source, str) else ""
        if key not in cls._SOURCE_CONFIG:
            raise ValueError("unsupported collection budget source")
        return key

    @staticmethod
    def _positive_number(value: object, name: str) -> float:
        if type(value) not in {int, float} or not isfinite(float(value)) or value <= 0:
            raise ValueError(f"{name} must be a finite positive number")
        return float(value)


class CollectionContext:
    """One row's state; create before pre-auth and retain through post-collection work."""

    def __init__(
        self,
        target: CameraTarget,
        config: object,
        *,
        transport_factory: Callable[[CollectionContext], TransportPolicy] | None = None,
        cancel_event: threading.Event | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.target = target
        self.config = config
        self.cancel_event = cancel_event or threading.Event()
        self.started_monotonic = clock()
        self.budget = CollectionBudget(config, started_at=self.started_monotonic, clock=clock)
        self.auth = AuthenticationLedger()
        self.report = CollectionReport()
        self._clock = clock
        self._transport: TransportPolicy | None = None
        self._transport_factory = transport_factory
        self._resources: list[object] = []
        self._closed = False
        self._lock = threading.RLock()
        if transport_factory is not None:
            self._transport = transport_factory(self)

    @property
    def transport(self) -> TransportPolicy:
        if self._transport is None:
            raise RuntimeError("target transport policy was not configured")
        return self._transport

    @property
    def cancelled(self) -> bool:
        return self.cancel_event.is_set()

    def check(self, source: str) -> float:
        if self.cancel_event.is_set():
            raise CollectionCancelled("coleta cancelada")
        remaining = self.budget.remaining(source)
        if remaining <= 0:
            raise CollectionDeadlineExceeded("deadline cooperativo esgotado")
        return remaining

    def request_timeout(
        self, source: str, connect_cap: float | None = None, read_cap: float | None = None
    ) -> tuple[float, float]:
        self.check(source)
        connect = connect_cap or getattr(self.config, "connect_timeout_seconds", 3.0)
        read = read_cap or getattr(self.config, "request_timeout_seconds", 7.0)
        return self.budget.request_timeout(source, connect, read)

    def charge_operation(self, source: str, elapsed: float) -> None:
        self.budget.charge(source, elapsed)

    def merge(self, report: CollectionReport) -> CollectionReport:
        if not isinstance(report, CollectionReport):
            raise TypeError("collection context accepts only CollectionReport")
        with self._lock:
            self.report = self.report.merged(report)
            if report.cancelled:
                self.cancel_event.set()
            return self.report

    def register(self, resource: object) -> object:
        close = getattr(resource, "close", None)
        if not callable(close):
            raise TypeError("managed resource must expose close()")
        with self._lock:
            if self._closed:
                close()
                raise RuntimeError("collection context is already closed")
            self._resources.append(resource)
        return resource

    def snapshot_eligible(self, family: str) -> bool:
        """Eligibility is explicit and never inferred from CameraResult status."""
        if self.cancel_event.is_set() or not self.auth.allows_authenticated_request(family):
            return False
        return self.budget.remaining("SNAPSHOT_HTTP") > 0 or self.budget.remaining("RTSP_OPEN") > 0

    def close(self) -> bool:
        with self._lock:
            if self._closed:
                return True
            self._closed = True
            resources, self._resources = self._resources, []
        succeeded = True
        for resource in reversed(resources):
            try:
                resource.close()  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001 - do not leak raw close exceptions or secrets.
                succeeded = False
        return succeeded

    def __repr__(self) -> str:
        return (
            f"CollectionContext(target_ip={self.target.ip!r}, started_monotonic="
            f"{self.started_monotonic!r}, auth_state={self.auth.state!r})"
        )
