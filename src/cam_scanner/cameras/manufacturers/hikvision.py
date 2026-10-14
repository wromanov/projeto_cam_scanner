"""Bounded, read-only Hikvision ISAPI identity collection."""
from __future__ import annotations

import ipaddress
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterable
from typing import Any

import requests
from requests.auth import HTTPDigestAuth
from requests.exceptions import (
    ConnectionError,
    ConnectTimeout,
    ReadTimeout,
    RequestException,
    SSLError,
    Timeout,
)
from requests.utils import parse_dict_header

from cam_scanner.domain.models import (
    CameraResult,
    CameraTarget,
    CollectionAttempt,
    CollectionReport,
    EvidenceRecord,
)

_OPERATION = "GET /ISAPI/System/deviceInfo"
_MAX_XML_BYTES = 64 * 1024
_MAX_FIELD_LENGTH = 256
_TIMEOUT = (3.0, 7.0)


class HikvisionAdapter:
    """Query only GET /ISAPI/System/deviceInfo using bounded HTTP Digest."""

    def __init__(self, session_factory: Callable[[], Any] | None = None, timeout: tuple[float, float] = _TIMEOUT) -> None:
        self._session_factory = session_factory or requests.Session
        self._timeout = timeout

    def collect(self, target: CameraTarget) -> CameraResult:
        return self.collect_report(target).to_camera_result(target.ip)

    def collect_report(self, target: CameraTarget) -> CollectionReport:
        report = CollectionReport()
        started = time.monotonic()
        auth = _BoundedDigestAuth(target.username, target.password)
        try:
            address = ipaddress.ip_address(target.ip)
            host = f"[{address.compressed}]" if address.version == 6 else address.compressed
            with self._session_factory() as session:
                session.trust_env = False
                response = session.get(
                    f"http://{host}:80/ISAPI/System/deviceInfo",
                    auth=auth,
                    allow_redirects=False,
                    stream=True,
                    timeout=self._timeout,
                    verify=True,
                )
                try:
                    status = response.status_code
                    if 300 <= status < 400:
                        return self._failure(report, started, "INVALID_RESPONSE", "HTTP", status)
                    if status == 401:
                        category = "AUTH_MECHANISM_UNSUPPORTED" if auth.mechanism_unsupported else "AUTH_REJECTED"
                        return self._failure(report, started, category, "AUTH", status)
                    if status == 403:
                        return self._failure(report, started, "AUTHORIZATION_DENIED", "AUTH", status)
                    if status in {404, 405}:
                        return self._failure(report, started, "ENDPOINT_UNSUPPORTED", "HTTP", status, "SKIPPED")
                    if status != 200:
                        return self._failure(report, started, "HTTP_ERROR", "HTTP", status)
                    declared = response.headers.get("content-length")
                    if declared and int(declared) > _MAX_XML_BYTES:
                        return self._failure(report, started, "INVALID_RESPONSE", "PARSE", status)
                    body = _read_limited(response.iter_content(chunk_size=8192), _MAX_XML_BYTES)
                finally:
                    response.close()
        except ConnectTimeout:
            return self._failure(report, started, "CONNECT_TIMEOUT", "CONNECT")
        except (ReadTimeout, Timeout):
            return self._failure(report, started, "READ_TIMEOUT", "HTTP")
        except ValueError:
            return self._failure(report, started, "INVALID_RESPONSE", "PARSE")
        except requests.exceptions.InvalidURL:
            return self._failure(report, started, "INVALID_RESPONSE", "CONNECT")
        except SSLError:
            return self._failure(report, started, "TLS_ERROR", "CONNECT")
        except (ConnectionError, RequestException, OSError):
            return self._failure(report, started, "CONNECTION_REFUSED", "CONNECT")
        except Exception:  # noqa: BLE001 - raw transport and parser data is never retained.
            return self._failure(report, started, "UNEXPECTED", "HTTP")

        try:
            parsed = _parse_device_info(body)
        except (ET.ParseError, ValueError):
            return self._failure(report, started, "INVALID_RESPONSE", "PARSE", status)
        sensitive = (target.username, target.password)
        evidence = tuple(
            EvidenceRecord(
                field=field_name,
                value=value,
                source="VENDOR",
                confidence="STRONG",
                protocol="HTTP",
                operation=_OPERATION,
            )
            for field_name, value in parsed.items()
        )
        report = report.with_evidence(*evidence).validated_for_target(sensitive)
        if not any(record.field == "manufacturer" for record in report.evidence):
            return self._failure(report, started, "INVALID_RESPONSE", "PARSE", status)
        report = report.with_attempt(
            CollectionAttempt(
                stage="PARSE",
                operation=_OPERATION,
                protocol="HTTP",
                outcome="SUCCESS",
                duration=max(0.0, time.monotonic() - started),
                http_status=status,
                authentication_mechanism="HTTP_DIGEST",
            )
        )
        return report

    @staticmethod
    def _failure(
        report: CollectionReport,
        started: float,
        category: str,
        stage: str,
        status: int | None = None,
        outcome: str = "FAILED",
    ) -> CollectionReport:
        return report.with_attempt(
            CollectionAttempt(
                stage=stage,
                operation=_OPERATION,
                protocol="HTTP",
                outcome=outcome,
                duration=max(0.0, time.monotonic() - started),
                http_status=status,
                error_category=category,
                authentication_mechanism="HTTP_DIGEST",
            )
        )


def _read_limited(chunks: Iterable[bytes], limit: int) -> bytes:
    body = bytearray()
    for chunk in chunks:
        body.extend(chunk)
        if len(body) > limit:
            raise ValueError("response too large")
    return bytes(body)


class _BoundedDigestAuth(HTTPDigestAuth):
    """Retry once only after a supported Digest challenge."""

    def __init__(self, username: str, password: str) -> None:
        super().__init__(username, password)
        self.mechanism_unsupported = False
        self._challenge_seen = False

    def handle_401(self, response, **kwargs):
        challenges = response.headers.get("www-authenticate", "")
        digest = next(
            (item for item in _split_challenges(challenges) if item.casefold().startswith("digest ")),
            None,
        )
        parsed = parse_dict_header(digest[7:]) if digest else {}
        qop = {item.strip().casefold() for item in parsed.get("qop", "").split(",")}
        supported = bool(parsed.get("nonce")) and (not qop or "auth" in qop) and parsed.get("algorithm", "MD5").casefold() in {"md5", "md5-sess"}
        if response.status_code != 401:
            return response
        if self._challenge_seen or not supported:
            self.mechanism_unsupported = not supported
            return response
        self._challenge_seen = True
        return super().handle_401(response, **kwargs)


def _split_challenges(value: str) -> list[str]:
    chunks: list[str] = []
    start = 0
    quoted = False
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
        elif char == "\\" and quoted:
            escaped = True
        elif char == '"':
            quoted = not quoted
        elif char == "," and not quoted:
            remainder = value[index + 1 :].lstrip()
            if remainder.split(" ", 1)[0].casefold() in {"digest", "basic", "bearer", "negotiate"}:
                chunks.append(value[start:index].strip())
                start = index + 1
    chunks.append(value[start:].strip())
    return [chunk for chunk in chunks if chunk]


def _parse_device_info(body: bytes) -> dict[str, str]:
    if not body or len(body) > _MAX_XML_BYTES:
        raise ValueError("invalid response length")
    upper = body.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise ValueError("DTD is not allowed")
    root = ET.fromstring(body)
    names = {
        "devicename": "hostname",
        "model": "model",
        "serialnumber": "serial",
        "firmwareversion": "firmware",
        "macaddress": "mac",
        "manufacturer": "manufacturer",
    }
    values: dict[str, str] = {}
    for element in root.iter():
        field_name = names.get(element.tag.rsplit("}", 1)[-1].casefold())
        value = " ".join((element.text or "").split())
        if field_name and value and len(value) <= _MAX_FIELD_LENGTH and field_name not in values:
            values[field_name] = value
    return values
