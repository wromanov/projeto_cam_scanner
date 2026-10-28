"""Bounded, read-only Panasonic/i-PRO CGI identity collection.

The i-PRO Command Interface documents GET ``/cgi-bin/getinfo?FILE=1`` and
the NAME, SERIAL, and VERSION response fields (Command Interface v1.17, §9.1).
It does not identify the manufacturer in those fields, so this adapter does not
invent manufacturer evidence and can report only partial identity.
"""
from __future__ import annotations

import ipaddress
import re
import time
from collections.abc import Callable
from typing import Any

import requests
from requests.exceptions import ConnectTimeout, ReadTimeout, RequestException, SSLError, Timeout

from cam_scanner.application.collection_context import (
    CollectionCancelled,
    CollectionDeadlineExceeded,
)
from cam_scanner.cameras.manufacturers._http_utils import (
    DeadlineExceeded,
    bounded_timeout,
    managed_vendor_session,
    read_limited_until,
    remaining_budget,
    transport_provenance,
)
from cam_scanner.cameras.manufacturers.hikvision import _BoundedDigestAuth
from cam_scanner.domain.models import (
    CameraResult,
    CameraTarget,
    CollectionAttempt,
    CollectionReport,
    EvidenceRecord,
    is_valid_evidence_value,
)

_PATH = "/cgi-bin/getinfo?FILE=1"
_OPERATION = "GET /cgi-bin/getinfo"
_MAX_BODY = 16 * 1024
_MAX_FIELD_LENGTH = 256
_TIMEOUT = (3.0, 7.0)
_NATIVE_BUDGET = 10.0
_SUPPORTED_PROFILE = "i-pro-command-interface-v1.17:WV-S2531L"


class PanasonicAdapter:
    """Read model, serial, and firmware through the documented CGI endpoint."""

    def __init__(
        self,
        session_factory: Callable[[], Any] | None = None,
        timeout: tuple[float, float] = _TIMEOUT,
        budget: float = _NATIVE_BUDGET,
        profile: str | None = None,
    ) -> None:
        if (
            len(timeout) != 2
            or any(type(value) not in {int, float} or value <= 0 for value in timeout)
        ):
            raise ValueError("timeouts must be positive connect/read values")
        self._session_factory = session_factory or requests.Session
        self._timeout = timeout
        self._budget = budget
        self.profile = profile

    def collect(self, target: CameraTarget, *, context: Any = None) -> CameraResult:
        return self.collect_report(target, context=context).to_camera_result(target.ip)

    def collect_report(self, target: CameraTarget, *, context: Any = None) -> CollectionReport:
        started = time.monotonic()
        report = CollectionReport()
        try:
            address = ipaddress.ip_address(target.ip)
            host = f"[{address.compressed}]" if address.version == 6 else address.compressed
        except ValueError:
            return self._failure(report, started, "INVALID_INPUT", "VALIDATE")
        selected_profile = getattr(context, "panasonic_profile", None) if context is not None else None
        if selected_profile is None:
            selected_profile = self.profile
        if selected_profile != _SUPPORTED_PROFILE:
            return self._failure(report, started, "ENDPOINT_UNSUPPORTED", "HTTP",
                                 outcome="SKIPPED")
        auth = _BoundedDigestAuth(target.username, target.password)
        protocol: str | None = None
        metadata: dict[str, str] = {}

        try:
            with managed_vendor_session(context, "vendor_panasonic", self._session_factory) as session:
                session.trust_env = False
                timeout = bounded_timeout(self._timeout, started, self._budget)
                url = (context.transport.endpoint("vendor_panasonic", path=_PATH)
                       if context is not None else f"https://{host}{_PATH}")
                protocol, metadata = transport_provenance(
                    context, "vendor_panasonic", url,
                    auth_mode="NATIVE_DIGEST_EXISTING",
                )
                response = session.get(
                    # No HTTP downgrade: the target model has no explicit
                    # scheme setting, so use verified HTTPS on the default port.
                    url,
                    auth=auth,
                    allow_redirects=False,
                    stream=True,
                    timeout=timeout,
                    verify=True,
                )
                try:
                    status = response.status_code
                    category, stage, outcome = _classify_status(
                        status, auth.mechanism_unsupported
                    )
                    if category is not None:
                        return self._failure(report, started, category, stage, status, outcome,
                                              protocol=protocol, metadata=metadata)
                    declared = response.headers.get("content-length")
                    if declared and int(declared) > _MAX_BODY:
                        return self._failure(
                            report, started, "INVALID_RESPONSE", "PARSE", status,
                            protocol=protocol, metadata=metadata,
                        )
                    body = read_limited_until(
                        response.iter_content(chunk_size=4096), _MAX_BODY, started, self._budget,
                        context=context,
                    )
                finally:
                    response.close()
        except (DeadlineExceeded, CollectionDeadlineExceeded):
            return self._failure(report, started, "DEADLINE_EXCEEDED", "HTTP", protocol=protocol, metadata=metadata)
        except CollectionCancelled:
            return self._cancelled(report, started, protocol, metadata)
        except ConnectTimeout:
            return self._failure(report, started, "CONNECT_TIMEOUT", "CONNECT", protocol=protocol, metadata=metadata)
        except (ReadTimeout, Timeout):
            return self._failure(report, started, "READ_TIMEOUT", "HTTP", protocol=protocol, metadata=metadata)
        except SSLError:
            return self._failure(report, started, "TLS_ERROR", "CONNECT", protocol=protocol, metadata=metadata)
        except (RequestException, OSError):
            return self._failure(report, started, "CONNECTION_REFUSED", "CONNECT", protocol=protocol, metadata=metadata)
        except (ValueError, UnicodeDecodeError):
            return self._failure(report, started, "INVALID_RESPONSE", "PARSE", protocol=protocol, metadata=metadata)
        except Exception:  # noqa: BLE001 - raw transport details never enter reports.
            return self._failure(report, started, "UNEXPECTED", "HTTP", protocol=protocol, metadata=metadata)

        try:
            remaining_budget(started, self._budget)
            values = _parse_info(body)
        except DeadlineExceeded:
            return self._failure(report, started, "DEADLINE_EXCEEDED", "PARSE", status, protocol=protocol, metadata=metadata)
        except (ValueError, UnicodeDecodeError):
            return self._failure(report, started, "INVALID_RESPONSE", "PARSE", status, protocol=protocol, metadata=metadata)

        sensitive = (target.username, target.password)
        evidence = tuple(
            EvidenceRecord(
                field=field,
                value=value,
                source="VENDOR",
                confidence="STRONG",
                protocol=protocol,
                operation=_OPERATION,
            )
            for field, value in values.items()
            if is_valid_evidence_value(field, value, sensitive_values=sensitive)
        )
        report = report.with_evidence(*evidence).validated_for_target(sensitive)
        if not values:
            return self._failure(report, started, "INVALID_RESPONSE", "PARSE", status,
                                 protocol=protocol, metadata=metadata)
        return report.with_attempt(
            CollectionAttempt(
                stage="PARSE",
                operation=_OPERATION,
                protocol=protocol,
                outcome="SUCCESS",
                duration=max(0.0, time.monotonic() - started),
                http_status=status,
                authentication_mechanism="HTTP_DIGEST",
                metadata=metadata,
            )
        )

    @staticmethod
    def _failure(
        report: CollectionReport,
        started: float,
        category: str,
        stage: str,
        status: int | None = None,
        outcome: str = "FAILED",
        protocol: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> CollectionReport:
        return report.with_attempt(
            CollectionAttempt(
                stage=stage,
                operation=_OPERATION,
                protocol=protocol,
                outcome=outcome,
                duration=max(0.0, time.monotonic() - started),
                http_status=status,
                error_category=category,
                authentication_mechanism="HTTP_DIGEST",
                metadata=metadata or {},
            )
        )

    @staticmethod
    def _cancelled(report: CollectionReport, started: float, protocol: str | None,
                   metadata: dict[str, str]) -> CollectionReport:
        return report.with_attempt(CollectionAttempt(
            stage="HTTP", operation=_OPERATION, protocol=protocol, outcome="CANCELLED",
            duration=max(0.0, time.monotonic() - started),
            authentication_mechanism="HTTP_DIGEST", metadata=metadata,
        ))


def _classify_status(
    status: int, unsupported_auth: bool
) -> tuple[str | None, str, str]:
    if 300 <= status < 400:
        return "INVALID_RESPONSE", "HTTP", "FAILED"
    if status == 401:
        return (
            "AUTH_MECHANISM_UNSUPPORTED" if unsupported_auth else "AUTH_REJECTED",
            "AUTH",
            "FAILED",
        )
    if status == 403:
        return "AUTHORIZATION_DENIED", "AUTH", "FAILED"
    if status in {404, 405}:
        return "ENDPOINT_UNSUPPORTED", "HTTP", "SKIPPED"
    if status != 200:
        return "HTTP_ERROR", "HTTP", "FAILED"
    return None, "PARSE", "SUCCESS"


def _parse_info(body: bytes) -> dict[str, str]:
    if not body or len(body) > _MAX_BODY:
        raise ValueError("invalid response length")
    text = body.decode("utf-8-sig", errors="strict")
    values: dict[str, str] = {}
    mapping = {"NAME": "model", "SERIAL": "serial", "VERSION": "firmware",
               "MAC": "mac", "MACADDRESS": "mac", "MAC_ADDRESS": "mac"}
    lines = text.splitlines()
    if lines and lines[0].strip().casefold() == "<html>":
        lines = lines[1:]
        if not lines or lines[-1].strip().casefold() != "</html>":
            raise ValueError("malformed CGI wrapper")
        lines = lines[:-1]
    elif any(line.strip().casefold() in {"<html>", "</html>"} for line in lines):
        raise ValueError("malformed CGI wrapper")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if "=" not in line:
            raise ValueError("malformed CGI response")
        key, raw = line.split("=", 1)
        field = mapping.get(key.strip().upper())
        value = " ".join(raw.split())
        if field is None:
            continue
        if field == "mac":
            value = _normalize_mac(value)
            if value is None:
                continue
        if field in values or not value or len(value) > _MAX_FIELD_LENGTH:
            raise ValueError("invalid CGI field")
        values[field] = value
    if not values:
        raise ValueError("no recognized CGI fields")
    return values


def _normalize_mac(value: str) -> str | None:
    compact = value.replace(":", "").replace("-", "")
    if len(compact) != 12 or re.fullmatch(r"[0-9A-Fa-f]{12}", compact) is None:
        return None
    if ":" in value and "-" in value:
        return None
    if ":" in value and len(value.split(":")) != 6:
        return None
    if "-" in value and len(value.split("-")) != 6:
        return None
    return ":".join(compact[index:index + 2].upper() for index in range(0, 12, 2))
