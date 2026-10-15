"""Bounded, read-only Hanwha SUNAPI device information collection.

Endpoint: https://www.hanwhavision.com/wp-content/uploads/2024/07/HanwhaVision_OpenPlatform_Programming_Guide_5.00.pdf
"""
from __future__ import annotations

import ipaddress
import json
import time
from collections.abc import Callable
from typing import Any

import requests
from requests.exceptions import ConnectTimeout, ReadTimeout, RequestException, SSLError, Timeout

from cam_scanner.cameras.manufacturers._http_utils import (
    DeadlineExceeded,
    bounded_timeout,
    managed_vendor_session,
    read_limited_until,
    remaining_budget,
)
from cam_scanner.cameras.manufacturers.axis import _classify_status
from cam_scanner.cameras.manufacturers.hikvision import _BoundedDigestAuth
from cam_scanner.domain.models import (
    CameraResult,
    CameraTarget,
    CollectionAttempt,
    CollectionReport,
    EvidenceRecord,
    is_valid_evidence_value,
)

_OPERATION = "GET /stw-cgi/system.cgi deviceinfo view"
_PATH = "/stw-cgi/system.cgi?msubmenu=deviceinfo&action=view"
_MAX_BODY = 64 * 1024
_MAX_FIELD = 256
_NATIVE_BUDGET = 10.0


class SamsungHanwhaAdapter:
    """Read the documented SUNAPI deviceinfo view, preserving explicit identity."""

    def __init__(self, session_factory: Callable[[], Any] | None = None,
                 timeout: tuple[float, float] = (3.0, 7.0), budget: float = _NATIVE_BUDGET) -> None:
        if len(timeout) != 2 or any(
            type(value) not in {int, float} or value <= 0 for value in (*timeout, budget)
        ):
            raise ValueError("timeouts and budget must be positive")
        self._session_factory = session_factory or requests.Session
        self._timeout = timeout
        self._budget = budget

    def collect(self, target: CameraTarget, *, context: Any = None) -> CameraResult:
        return self.collect_report(target, context=context).to_camera_result(target.ip)

    def collect_report(self, target: CameraTarget, *, context: Any = None) -> CollectionReport:
        started = time.monotonic()
        report = CollectionReport()
        auth = _BoundedDigestAuth(target.username, target.password)
        try:
            address = ipaddress.ip_address(target.ip)
            host = f"[{address.compressed}]" if address.version == 6 else address.compressed
        except ValueError:
            return self._failure(report, started, "INVALID_INPUT", "VALIDATE")
        try:
            with managed_vendor_session(context, "vendor_hanwha", self._session_factory) as session:
                session.trust_env = False
                timeout = bounded_timeout(self._timeout, started, self._budget)
                url = (context.transport.endpoint("vendor_hanwha", path=_PATH)
                       if context is not None else f"https://{host}{_PATH}")
                response = session.get(
                    url, auth=auth, allow_redirects=False,
                    stream=True, timeout=timeout, verify=True,
                )
                try:
                    status = response.status_code
                    category, stage, outcome = _classify_status(status, auth.mechanism_unsupported)
                    if category:
                        return self._failure(report, started, category, stage, status, outcome)
                    declared = response.headers.get("content-length")
                    if declared and int(declared) > _MAX_BODY:
                        return self._failure(report, started, "INVALID_RESPONSE", "PARSE", status)
                    body = read_limited_until(
                        response.iter_content(chunk_size=8192), _MAX_BODY, started, self._budget,
                        context=context,
                    )
                finally:
                    response.close()
        except DeadlineExceeded:
            return self._failure(report, started, "DEADLINE_EXCEEDED", "HTTP")
        except ConnectTimeout:
            return self._failure(report, started, "CONNECT_TIMEOUT", "CONNECT")
        except (ReadTimeout, Timeout):
            return self._failure(report, started, "READ_TIMEOUT", "HTTP")
        except SSLError:
            return self._failure(report, started, "TLS_ERROR", "CONNECT")
        except (RequestException, OSError):
            return self._failure(report, started, "CONNECTION_REFUSED", "CONNECT")
        except ValueError:
            return self._failure(report, started, "INVALID_RESPONSE", "PARSE")
        except Exception:  # noqa: BLE001 - never retain raw transport data
            return self._failure(report, started, "UNEXPECTED", "HTTP")
        try:
            remaining_budget(started, self._budget)
            values = _parse_device_info(body)
        except DeadlineExceeded:
            return self._failure(report, started, "DEADLINE_EXCEEDED", "PARSE", status)
        except (ValueError, UnicodeDecodeError):
            return self._failure(report, started, "INVALID_RESPONSE", "PARSE", status)
        sensitive = (target.username, target.password)
        records = tuple(
            EvidenceRecord(field=field, value=value, source="VENDOR", protocol="HTTPS",
                           operation=_OPERATION)
            for field, value in values.items()
            if is_valid_evidence_value(field, value, sensitive_values=sensitive)
        )
        report = report.with_evidence(*records).validated_for_target(sensitive)
        if not report.evidence:
            return self._failure(report, started, "INVALID_RESPONSE", "PARSE", status)
        return report.with_attempt(CollectionAttempt(
            stage="PARSE", operation=_OPERATION, protocol="HTTPS", outcome="SUCCESS",
            duration=max(0.0, time.monotonic() - started), http_status=status,
            authentication_mechanism="HTTP_DIGEST",
        ))

    @staticmethod
    def _failure(report: CollectionReport, started: float, category: str, stage: str,
                 status: int | None = None, outcome: str = "FAILED") -> CollectionReport:
        return report.with_attempt(CollectionAttempt(
            stage=stage, operation=_OPERATION, protocol="HTTPS", outcome=outcome,
            duration=max(0.0, time.monotonic() - started), http_status=status,
            error_category=category, authentication_mechanism="HTTP_DIGEST",
        ))


def _parse_device_info(body: bytes) -> dict[str, str]:
    if not body or len(body) > _MAX_BODY:
        raise ValueError("invalid response length")
    content = body.decode("utf-8-sig").strip()
    if content.startswith("{"):
        payload = json.loads(content)
        if not isinstance(payload, dict) or "error" in {key.casefold() for key in payload}:
            raise ValueError("vendor error")
        properties = payload
    else:
        properties: dict[str, str] = {}
        for line in content.splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key not in properties:
                properties[key] = value
    mapping = {"Manufacturer": "manufacturer", "Model": "model",
               "SerialNumber": "serial", "FirmwareVersion": "firmware"}
    values: dict[str, str] = {}
    for key, field in mapping.items():
        raw = properties.get(key)
        if isinstance(raw, str):
            value = " ".join(raw.split())
            if value and len(value) <= _MAX_FIELD:
                values[field] = value
    return values
