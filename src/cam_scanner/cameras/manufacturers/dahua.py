"""Read-only Dahua CGI identity collection.

The vendor documents its camera APIs at https://www.dahuasecurity.com/api/.
The authorized CGI operations are getSystemInfo (device type and serial) and
getVendor (manufacturer). No configuration or control operation is issued.
"""
from __future__ import annotations

import ipaddress
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

MAX_RESPONSE_BYTES = 16 * 1024
MAX_FIELD_LENGTH = 256
SYSTEM_PATH = "/cgi-bin/magicBox.cgi?action=getSystemInfo"
VENDOR_PATH = "/cgi-bin/magicBox.cgi?action=getVendor"
SYSTEM_OPERATION = "GET /cgi-bin/magicBox.cgi getSystemInfo"
VENDOR_OPERATION = "GET /cgi-bin/magicBox.cgi getVendor"


class DahuaAdapter:
    """Read model/serial and then vendor using only documented CGI GETs."""

    def __init__(
        self,
        session_factory: Callable[[], Any] | None = None,
        timeout: tuple[float, float] = (3.0, 7.0), budget: float = 10.0,
    ) -> None:
        if any(type(value) not in {int, float} or value <= 0 for value in (*timeout, budget)):
            raise ValueError("timeouts and budget must be positive")
        self.session_factory = session_factory or requests.Session
        self.timeout, self.budget = timeout, budget

    def collect(self, target: CameraTarget, *, context: Any = None) -> CameraResult:
        return self.collect_report(target, context=context).to_camera_result(target.ip)

    def collect_report(self, target: CameraTarget, *, context: Any = None) -> CollectionReport:
        report = CollectionReport()
        started = time.monotonic()
        try:
            address = ipaddress.ip_address(target.ip)
        except ValueError:
            return attempt(report, SYSTEM_OPERATION, started, "CONNECT", "FAILED", "INVALID_INPUT")
        host = f"[{address.compressed}]" if address.version == 6 else address.compressed
        # The target contract does not declare an HTTP scheme. Use TLS by
        # default and fail closed if the device/certificate is not compatible.
        origin = f"https://{host}"
        auth = _BoundedDigestAuth(target.username, target.password)
        protocol: str | None = None
        metadata: dict[str, str] = {}
        try:
            with managed_vendor_session(context, "vendor_dahua", self.session_factory) as session:
                session.trust_env = False
                for path, operation, mapping in (
                    (
                        SYSTEM_PATH,
                        SYSTEM_OPERATION,
                        {"serialNumber": "serial", "deviceType": "model"},
                    ),
                    (VENDOR_PATH, VENDOR_OPERATION, {"vendor": "manufacturer"}),
                ):
                    protocol = None
                    metadata = {}
                    try:
                        timeout = bounded_timeout(self.timeout, started, self.budget)
                    except DeadlineExceeded:
                        return attempt(report, operation, started, "HTTP", "FAILED", "DEADLINE_EXCEEDED", protocol=protocol, metadata=metadata)
                    try:
                        url = (context.transport.endpoint("vendor_dahua", path=path)
                               if context is not None else origin + path)
                        protocol, metadata = transport_provenance(
                            context, "vendor_dahua", url,
                            auth_mode="NATIVE_DIGEST_EXISTING",
                        )
                        response = session.get(
                            url, auth=auth, allow_redirects=False,
                            stream=True, timeout=timeout, verify=True,
                        )
                        try:
                            status = response.status_code
                            category = http_failure(status, auth.mechanism_unsupported)
                            if category:
                                outcome = "SKIPPED" if category == "ENDPOINT_UNSUPPORTED" else "FAILED"
                                stage = "AUTH" if status in {401, 403} else "HTTP"
                                return attempt(report, operation, started, stage, outcome, category, status, protocol, metadata)
                            length = response.headers.get("content-length")
                            if length and int(length) > MAX_RESPONSE_BYTES:
                                raise ValueError("oversized response")
                            body = read_limited_until(
                                response.iter_content(chunk_size=4096),
                                MAX_RESPONSE_BYTES,
                                started,
                                self.budget,
                                context=context,
                            )
                        finally:
                            response.close()
                    except DeadlineExceeded:
                        return attempt(report, operation, started, "HTTP", "FAILED", "DEADLINE_EXCEEDED", protocol=protocol, metadata=metadata)
                    except ConnectTimeout:
                        return attempt(report, operation, started, "CONNECT", "FAILED", "CONNECT_TIMEOUT", protocol=protocol, metadata=metadata)
                    except (ReadTimeout, Timeout):
                        return attempt(report, operation, started, "HTTP", "FAILED", "READ_TIMEOUT", protocol=protocol, metadata=metadata)
                    except SSLError:
                        return attempt(report, operation, started, "CONNECT", "FAILED", "TLS_ERROR", protocol=protocol, metadata=metadata)
                    except ValueError:
                        return attempt(report, operation, started, "PARSE", "FAILED", "INVALID_RESPONSE", protocol=protocol, metadata=metadata)
                    except (RequestException, OSError):
                        return attempt(report, operation, started, "CONNECT", "FAILED", "CONNECTION_REFUSED", protocol=protocol, metadata=metadata)

                    try:
                        remaining_budget(started, self.budget)
                        values = parse_key_values(body)
                    except DeadlineExceeded:
                        return attempt(report, operation, started, "PARSE", "FAILED", "DEADLINE_EXCEEDED", status, protocol, metadata)
                    except ValueError:
                        return attempt(report, operation, started, "PARSE", "FAILED", "INVALID_RESPONSE", status, protocol, metadata)
                    records = [
                        EvidenceRecord(
                            field=field, value=values[key], source="VENDOR",
                            confidence="STRONG", protocol=protocol, operation=operation,
                        )
                        for key, field in mapping.items()
                        if key in values and is_valid_evidence_value(
                            field, values[key], sensitive_values=(target.username, target.password)
                        )
                    ]
                    report = report.with_evidence(*records).validated_for_target(
                        (target.username, target.password)
                    )
                    if not records:
                        report = attempt(
                            report,
                            operation,
                            started,
                            "PARSE",
                            "FAILED",
                            "INVALID_RESPONSE",
                            status,
                            protocol,
                            metadata,
                        )
                        if operation == SYSTEM_OPERATION:
                            continue
                        return report
                    report = attempt(report, operation, started, "PARSE", "SUCCESS", None, status, protocol, metadata)
        except (DeadlineExceeded, CollectionDeadlineExceeded):
            return attempt(report, SYSTEM_OPERATION, started, "HTTP", "FAILED", "DEADLINE_EXCEEDED", protocol=protocol, metadata=metadata)
        except CollectionCancelled:
            return attempt(report, SYSTEM_OPERATION, started, "HTTP", "CANCELLED", None, protocol=protocol, metadata=metadata)
        except Exception:  # noqa: BLE001 - raw transport data must never enter reports.
            return attempt(report, SYSTEM_OPERATION, started, "HTTP", "FAILED", "UNEXPECTED", protocol=protocol, metadata=metadata)
        return report


def http_failure(status: int, unsupported_digest: bool) -> str | None:
    if status == 200:
        return None
    if status == 401:
        return "AUTH_MECHANISM_UNSUPPORTED" if unsupported_digest else "AUTH_REJECTED"
    if status == 403:
        return "AUTHORIZATION_DENIED"
    if status in {404, 405}:
        return "ENDPOINT_UNSUPPORTED"
    if 300 <= status < 400:
        return "INVALID_RESPONSE"
    return "HTTP_ERROR"


def parse_key_values(body: bytes) -> dict[str, str]:
    if not body or len(body) > MAX_RESPONSE_BYTES:
        raise ValueError("empty or oversized response")
    text = body.decode("utf-8", errors="strict")
    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if "=" not in line:
            raise ValueError("invalid CGI line")
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if key in values or not key or len(value) > MAX_FIELD_LENGTH:
            raise ValueError("invalid CGI field")
        values[key] = value
    if not values:
        raise ValueError("empty CGI values")
    return values


def attempt(
    report: CollectionReport, operation: str, started: float,
    stage: str, outcome: str, category: str | None, status: int | None = None,
    protocol: str | None = None, metadata: dict[str, str] | None = None,
) -> CollectionReport:
    return report.with_attempt(CollectionAttempt(
        stage=stage, operation=operation, protocol=protocol, outcome=outcome,
        duration=max(0.0, time.monotonic() - started), http_status=status,
        error_category=category, authentication_mechanism="HTTP_DIGEST",
        metadata=metadata or {},
    ))
