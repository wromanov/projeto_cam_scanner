"""Bounded, read-only Axis VAPIX Basic Device Information collection.

API: https://developer.axis.com/vapix/network-video/basic-device-information/
"""
from __future__ import annotations

import ipaddress
import json
import time
from collections.abc import Callable
from typing import Any

import requests
from requests.exceptions import ConnectTimeout, ReadTimeout, RequestException, SSLError, Timeout

from cam_scanner.application.collection_context import (
    CollectionCancelled,
    CollectionDeadlineExceeded,
    CollectionTLSFailure,
)
from cam_scanner.cameras.manufacturers._http_utils import (
    DeadlineExceeded,
    bounded_timeout,
    managed_vendor_session,
    read_limited_until,
    remaining_budget,
    transport_provenance,
)
from cam_scanner.domain.models import (
    CameraResult,
    CameraTarget,
    CollectionAttempt,
    CollectionReport,
    EvidenceRecord,
    is_valid_evidence_value,
)

_PATH = "/axis-cgi/basicdeviceinfo.cgi"
_VERSIONS_OPERATION = "POST /axis-cgi/basicdeviceinfo.cgi getSupportedVersions"
_PROPERTIES_OPERATION = "POST /axis-cgi/basicdeviceinfo.cgi getAllUnrestrictedProperties"
_VERSIONS_BODY = b'{"method":"getSupportedVersions"}'
_PROPERTIES_BODY = b'{"apiVersion":"1.2","method":"getAllUnrestrictedProperties"}'
_MAX_BODY = 64 * 1024
_MAX_FIELD = 256
_NATIVE_BUDGET = 10.0


class AxisAdapter:
    """Collect Axis identity through the anonymous VIEWER_SAFE BDI profile."""

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
        try:
            address = ipaddress.ip_address(target.ip)
            host = f"[{address.compressed}]" if address.version == 6 else address.compressed
        except ValueError:
            return self._failure(report, started, "INVALID_INPUT", "VALIDATE")
        try:
            protocol: str | None = None
            metadata: dict[str, str] = {}
            with managed_vendor_session(context, "vendor_axis", self._session_factory) as session:
                session.trust_env = False
                cookies = getattr(session, "cookies", None)
                if cookies is not None and callable(getattr(cookies, "clear", None)):
                    cookies.clear()
                timeout = bounded_timeout(self._timeout, started, self._budget)
                url = (context.transport.endpoint("vendor_axis", path=_PATH)
                       if context is not None else f"https://{host}{_PATH}")
                protocol, metadata = transport_provenance(
                    context, "vendor_axis", url, auth_mode="PUBLIC_NONE"
                )
                operation = _VERSIONS_OPERATION
                response = session.post(url, data=_VERSIONS_BODY,
                    headers={"Content-Type": "application/json"},
                    allow_redirects=False, stream=True, timeout=timeout, verify=True,
                    authenticated=False)
                try:
                    status = response.status_code
                    category, stage, outcome = _classify_status(status, False)
                    if category:
                        return self._failure(report, started, category, stage, status, outcome,
                                              operation, protocol=protocol, metadata=metadata)
                    declared = response.headers.get("content-length")
                    if declared and int(declared) > _MAX_BODY:
                        return self._failure(report, started, "INVALID_RESPONSE", "PARSE", status,
                                              operation=operation, protocol=protocol, metadata=metadata)
                    body = read_limited_until(
                        response.iter_content(chunk_size=8192), _MAX_BODY, started, self._budget,
                        context=context,
                    )
                finally:
                    response.close()
                try:
                    versions = _parse_supported_versions(body)
                except PermissionError:
                    if context is not None:
                        context.auth.observe_authorization_denied()
                    return self._failure(report, started, "AUTHORIZATION_DENIED", "HTTP", status,
                                         operation=operation, protocol=protocol, metadata=metadata)
                except LookupError:
                    return self._failure(report, started, "ENDPOINT_UNSUPPORTED", "HTTP", status,
                                         "SKIPPED", operation, protocol=protocol, metadata=metadata)
                except (TypeError, ValueError, UnicodeDecodeError):
                    return self._failure(report, started, "INVALID_RESPONSE", "PARSE", status,
                                         operation=operation, protocol=protocol, metadata=metadata)
                if "1.2" not in versions:
                    return self._failure(report, started, "ENDPOINT_UNSUPPORTED", "HTTP", status,
                                         "SKIPPED", operation, protocol=protocol, metadata=metadata)
                if context is not None:
                    context.check("NATIVE")
                    timeout = bounded_timeout(self._timeout, started, self._budget)
                operation = _PROPERTIES_OPERATION
                response = session.post(url, data=_PROPERTIES_BODY,
                    headers={"Content-Type": "application/json"},
                    allow_redirects=False, stream=True, timeout=timeout, verify=True,
                    authenticated=False)
                try:
                    status = response.status_code
                    category, stage, outcome = _classify_status(status, False)
                    if category:
                        return self._failure(report, started, category, stage, status, outcome,
                                             operation, protocol=protocol, metadata=metadata)
                    declared = response.headers.get("content-length")
                    if declared and int(declared) > _MAX_BODY:
                        return self._failure(report, started, "INVALID_RESPONSE", "PARSE", status,
                                             operation=operation, protocol=protocol, metadata=metadata)
                    body = read_limited_until(response.iter_content(chunk_size=8192), _MAX_BODY,
                        started, self._budget, context=context)
                finally:
                    response.close()
        except (DeadlineExceeded, CollectionDeadlineExceeded):
            return self._failure(report, started, "DEADLINE_EXCEEDED", "HTTP",
                                 operation=locals().get("operation", _VERSIONS_OPERATION),
                                  protocol=locals().get("protocol"), metadata=locals().get("metadata", {}))
        except CollectionCancelled:
            return report.with_attempt(CollectionAttempt(
                stage="HTTP", operation=locals().get("operation", _VERSIONS_OPERATION),
                protocol=locals().get("protocol"), outcome="CANCELLED",
                duration=max(0.0, time.monotonic() - started),
                authentication_mechanism="NONE",
                metadata=locals().get("metadata", {}),
            ))
        except CollectionTLSFailure:
            return self._failure(report, started, "TLS_ERROR", "CONNECT",
                                 operation=locals().get("operation", _VERSIONS_OPERATION),
                                  protocol=locals().get("protocol"), metadata=locals().get("metadata", {}))
        except ConnectTimeout:
            return self._failure(report, started, "CONNECT_TIMEOUT", "CONNECT",
                                 operation=locals().get("operation", _VERSIONS_OPERATION),
                                  protocol=locals().get("protocol"), metadata=locals().get("metadata", {}))
        except (ReadTimeout, Timeout):
            return self._failure(report, started, "READ_TIMEOUT", "HTTP",
                                 operation=locals().get("operation", _VERSIONS_OPERATION),
                                  protocol=locals().get("protocol"), metadata=locals().get("metadata", {}))
        except SSLError:
            return self._failure(report, started, "TLS_ERROR", "CONNECT",
                                 operation=locals().get("operation", _VERSIONS_OPERATION),
                                  protocol=locals().get("protocol"), metadata=locals().get("metadata", {}))
        except PermissionError:
            return self._failure(report, started, "AUTHORIZATION_DENIED", "HTTP", status,
                                 operation=locals().get("operation", _VERSIONS_OPERATION),
                                  protocol=locals().get("protocol"), metadata=locals().get("metadata", {}))
        except (RequestException, OSError):
            return self._failure(report, started, "CONNECTION_REFUSED", "CONNECT",
                                 operation=locals().get("operation", _VERSIONS_OPERATION),
                                  protocol=locals().get("protocol"), metadata=locals().get("metadata", {}))
        except ValueError:
            return self._failure(report, started, "INVALID_RESPONSE", "PARSE",
                                 operation=locals().get("operation", _VERSIONS_OPERATION),
                                  protocol=locals().get("protocol"), metadata=locals().get("metadata", {}))
        except Exception:  # noqa: BLE001 - never retain raw transport data
            return self._failure(report, started, "UNEXPECTED", "HTTP",
                                  protocol=locals().get("protocol"), metadata=locals().get("metadata", {}))
        try:
            remaining_budget(started, self._budget)
            values = _parse_properties(body)
        except PermissionError:
            if context is not None:
                context.auth.observe_authorization_denied()
            return self._failure(report, started, "AUTHORIZATION_DENIED", "HTTP", status,
                                 operation=_PROPERTIES_OPERATION,
                                  protocol=locals().get("protocol"), metadata=locals().get("metadata", {}))
        except LookupError:
            return self._failure(report, started, "ENDPOINT_UNSUPPORTED", "HTTP", status,
                                 "SKIPPED", _PROPERTIES_OPERATION,
                                  protocol=locals().get("protocol"), metadata=locals().get("metadata", {}))
        except DeadlineExceeded:
            return self._failure(report, started, "DEADLINE_EXCEEDED", "PARSE", status,
                                 operation=_PROPERTIES_OPERATION,
                                  protocol=locals().get("protocol"), metadata=locals().get("metadata", {}))
        except (TypeError, ValueError, UnicodeDecodeError):
            return self._failure(report, started, "INVALID_RESPONSE", "PARSE", status,
                                 operation=_PROPERTIES_OPERATION,
                                 protocol=locals().get("protocol"), metadata=locals().get("metadata", {}))
        sensitive = (target.username, target.password)
        records = tuple(
            EvidenceRecord(field=field, value=value, source="VENDOR", protocol=protocol,
                           operation=_PROPERTIES_OPERATION)
            for field, value in values.items()
            if is_valid_evidence_value(field, value, sensitive_values=sensitive)
        )
        report = report.with_evidence(*records).validated_for_target(sensitive)
        if not report.evidence:
            return self._failure(report, started, "INVALID_RESPONSE", "PARSE", status,
                                 operation=_PROPERTIES_OPERATION,
                                 protocol=locals().get("protocol"), metadata=locals().get("metadata", {}))
        return report.with_attempt(CollectionAttempt(
            stage="PARSE", operation=_PROPERTIES_OPERATION, protocol=protocol, outcome="SUCCESS",
            duration=max(0.0, time.monotonic() - started), http_status=status,
            authentication_mechanism="NONE", metadata=metadata,
        ))

    @staticmethod
    def _failure(report: CollectionReport, started: float, category: str, stage: str,
                 status: int | None = None, outcome: str = "FAILED", operation: str = _PROPERTIES_OPERATION,
                 protocol: str | None = None, metadata: dict[str, str] | None = None) -> CollectionReport:
        return report.with_attempt(CollectionAttempt(
            stage=stage, operation=operation, protocol=protocol, outcome=outcome,
            duration=max(0.0, time.monotonic() - started), http_status=status,
            error_category=category, authentication_mechanism="NONE", metadata=metadata or {},
        ))


def _parse_supported_versions(body: bytes) -> list[str]:
    if not body or len(body) > _MAX_BODY:
        raise ValueError("invalid response length")
    payload = json.loads(body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("vendor error")
    if "error" in payload:
        error = payload["error"]
        code = error.get("code") if isinstance(error, dict) else None
        if code == 2001:
            raise PermissionError("authorization denied")
        if code in {2003, 2004}:
            raise LookupError("operation unsupported")
        raise TypeError("vendor error")
    data = payload.get("data")
    versions = data.get("apiVersions") if isinstance(data, dict) else None
    if not isinstance(versions, list) or any(not isinstance(v, str) for v in versions):
        raise ValueError("invalid API version list")
    return versions


def _classify_status(status: int, unsupported_auth: bool) -> tuple[str | None, str, str]:
    if 300 <= status < 400:
        return "INVALID_RESPONSE", "HTTP", "FAILED"
    if status == 401:
        return "HTTP_ERROR", "HTTP", "FAILED"
    if status == 403:
        return "AUTHORIZATION_DENIED", "AUTH", "FAILED"
    if status in {404, 405}:
        return "ENDPOINT_UNSUPPORTED", "HTTP", "SKIPPED"
    if status != 200:
        return "HTTP_ERROR", "HTTP", "FAILED"
    return None, "PARSE", "SUCCESS"


def _parse_properties(body: bytes) -> dict[str, str]:
    if not body or len(body) > _MAX_BODY:
        raise ValueError("invalid response length")
    payload = json.loads(body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("vendor error")
    if "error" in payload:
        error = payload["error"]
        code = error.get("code") if isinstance(error, dict) else None
        if code == 2001:
            raise PermissionError("authorization denied")
        if code in {2003, 2004}:
            raise LookupError("operation unsupported")
        raise ValueError("vendor error")
    data = payload.get("data")
    properties = data.get("propertyList") if isinstance(data, dict) else None
    if not isinstance(properties, dict):
        raise TypeError("missing property list")
    mapping = {
        "Brand": "manufacturer",
        "SerialNumber": "serial",
        "Version": "firmware",
        "HardwareID": "hardware_id",
    }
    values: dict[str, str] = {}
    for key, field in mapping.items():
        raw = properties.get(key)
        if isinstance(raw, str):
            value = " ".join(raw.split())
            if value and len(value) <= _MAX_FIELD:
                values[field] = value
    for key in ("ProdFullName", "ProdNbr", "ProdShortName"):
        raw = properties.get(key)
        if isinstance(raw, str):
            value = " ".join(raw.split())
            if value and len(value) <= _MAX_FIELD:
                values["model"] = value
                break
    return values
