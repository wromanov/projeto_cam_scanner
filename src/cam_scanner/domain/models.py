"""Domain data contracts for camera inputs, evidence, reports, and public results."""
from __future__ import annotations

import ipaddress
import re
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from math import isfinite
from types import MappingProxyType

from cam_scanner.domain.enums import CollectionMethod, CollectionStatus, ErrorCode

_IDENTITY_FIELDS = ("manufacturer", "model", "serial")
_VALID_CONFIDENCE = {"STRONG", "WEAK"}
_VALID_STAGES = {"DISCOVERY", "CONNECT", "HTTP", "AUTH", "SOAP", "PARSE", "MERGE", "VALIDATE"}
_VALID_OUTCOMES = {"SUCCESS", "FAILED", "CANCELLED", "SKIPPED"}
_VALID_ERROR_CATEGORIES = {
    "CONNECT_TIMEOUT",
    "READ_TIMEOUT",
    "CONNECTION_REFUSED",
    "TLS_ERROR",
    "HTTP_ERROR",
    "AUTH_REJECTED",
    "AUTHORIZATION_DENIED",
    "AUTH_MECHANISM_UNSUPPORTED",
    "ENDPOINT_UNSUPPORTED",
    "SOAP_FAULT",
    "INVALID_RESPONSE",
    "DEADLINE_EXCEEDED",
    "INVALID_INPUT",
    "UNEXPECTED",
}
_PLACEHOLDERS = {"", "-", "n/a", "na", "none", "null", "unknown", "not available"}
_URL_IN_EVIDENCE = re.compile(r"(?i)\b(?:[a-z][a-z0-9+.-]{1,20}://|www\.)")
_EXPLICIT_SECRET = re.compile(
    r"(?i)(?:\b(?:password|passwd|pwd|username|user|token|api[_-]?key|authorization)\b"
    r"\s*(?:=|:)\s*|\bauthorization\s*:\s*(?:basic|bearer)\b)"
)
_VALID_EVIDENCE_FIELDS = {
    "hostname",
    "manufacturer",
    "manufacturer_original",
    "model",
    "serial",
    "firmware",
    "hardware_id",
    "mac",
    "manufacturer_signal",
    "onvif_reachable",
}
_USEFUL_EVIDENCE_FIELDS = {
    "hostname",
    "manufacturer",
    "manufacturer_original",
    "model",
    "serial",
    "firmware",
    "hardware_id",
    "mac",
}
_SAFE_OPERATION = re.compile(r"^[A-Za-z0-9_./: -]{1,80}$")
_VALID_OPERATIONS = {
    "GetCapabilities",
    "GetSystemDateAndTime",
    "GetDeviceInformation",
    "create_onvif_client",
    "validate_target",
    "collect_one",
    "collect",
    "collect_result",
    "collect_report",
    "parse_device_information",
    "resolve_preauth_manufacturer",
    "aggregate_collection_report",
    "discover",
    "ONVIF pre-authentication discovery",
    "GET /ISAPI/System/deviceInfo",
    "POST /axis-cgi/basicdeviceinfo.cgi getAllProperties",
    "GET /stw-cgi/system.cgi deviceinfo view",
    "GET /cgi-bin/magicBox.cgi getSystemInfo",
    "GET /cgi-bin/magicBox.cgi getVendor",
    "GET /cgi-bin/getinfo",
}
_VALID_PROTOCOLS = {"ONVIF", "HTTP", "HTTPS", "RTSP"}
_VALID_EVIDENCE_SOURCES = {
    "ONVIF_PREAUTH",
    "ONVIF",
    "ONVIF_AUTHENTICATED",
    "LEGACY",
    "FIXTURE",
    "SECOND_SOURCE",
    "VENDOR",
}
_SAFE_METADATA_KEYS = {
    "service",
    "transport",
    "scheme",
    "port",
    "vendor_family",
    "soap_code",
    "retry_policy",
}
_SAFE_CODE = re.compile(
    r"^(?:[A-Za-z][A-Za-z0-9]{0,7}:)?(?:Sender|Receiver|MustUnderstand|VersionMismatch|"
    r"NotAuthorized|InvalidArgVal|ActionNotSupported|OperationProhibited|ResourceUnknown)$|"
    r"^(?:0x[0-9A-Fa-f]{1,8}|E[0-9]{1,6})$"
)


def is_valid_evidence_value(
    field_name: str, value: object, *, sensitive_values: tuple[str, ...] = ()
) -> bool:
    """Reject empty, secret-bearing, URL-shaped, or placeholder values at ingress."""
    if not isinstance(value, str):
        return False
    cleaned = " ".join(value.split())
    if cleaned.casefold() in _PLACEHOLDERS:
        return False
    if _URL_IN_EVIDENCE.search(cleaned) or _EXPLICIT_SECRET.search(cleaned):
        return False
    folded_value = value.casefold()
    for secret in sensitive_values:
        if not isinstance(secret, str) or not secret:
            continue
        if secret.casefold() in folded_value:
            return False
    if field_name == "mac":
        return bool(re.fullmatch(r"(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}", cleaned))
    return bool(cleaned)


def _error_code_for_category(category: str | None) -> ErrorCode:
    if category in {"CONNECT_TIMEOUT", "READ_TIMEOUT", "DEADLINE_EXCEEDED"}:
        return ErrorCode.TIMEOUT
    if category in {"CONNECTION_REFUSED", "TLS_ERROR"}:
        return ErrorCode.NETWORK_ERROR
    if category in {"AUTH_REJECTED", "AUTHORIZATION_DENIED", "AUTH_MECHANISM_UNSUPPORTED"}:
        return ErrorCode.AUTH_ERROR
    if category in {"SOAP_FAULT", "ENDPOINT_UNSUPPORTED", "INVALID_RESPONSE", "HTTP_ERROR"}:
        return ErrorCode.ONVIF_ERROR
    if category == "INVALID_INPUT":
        return ErrorCode.INVALID_INPUT
    return ErrorCode.UNEXPECTED_ERROR


@dataclass(frozen=True, slots=True)
class CameraTarget:
    ip: str
    username: str
    password: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    """One validated value and its source; value is omitted from object reprs."""

    field: str
    value: str = field(repr=False)
    source: str
    confidence: str = "STRONG"
    protocol: str | None = None
    operation: str | None = None
    observed_at: datetime = field(default_factory=lambda: datetime.now(UTC), repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.field, str) or not self.field.strip():
            raise ValueError("evidence field must be non-empty text")
        if self.field not in _VALID_EVIDENCE_FIELDS:
            raise ValueError("evidence field is not part of the approved collection schema")
        if not is_valid_evidence_value(self.field, self.value):
            raise ValueError("evidence value must be validated and non-empty")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("evidence source must be non-empty text")
        if self.source not in _VALID_EVIDENCE_SOURCES:
            object.__setattr__(self, "source", "SANITIZED_SOURCE")
        if self.protocol not in {None, *_VALID_PROTOCOLS}:
            object.__setattr__(self, "protocol", None)
        if self.operation not in {None, *_VALID_OPERATIONS}:
            object.__setattr__(self, "operation", "operation")
        if self.confidence not in _VALID_CONFIDENCE:
            raise ValueError("evidence confidence must be STRONG or WEAK")
        if self.field == "manufacturer" and self.confidence != "STRONG":
            raise ValueError("manufacturer identity evidence must be strong")
        if self.field == "manufacturer_signal" and self.confidence != "WEAK":
            raise ValueError("manufacturer signal evidence must be weak")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("evidence timestamp must include a timezone")


@dataclass(frozen=True, slots=True)
class CollectionAttempt:
    """Sanitized diagnostics for one operation; never stores raw exceptions or payloads."""

    stage: str
    operation: str
    outcome: str
    duration: float = 0.0
    protocol: str | None = None
    authentication_mechanism: str | None = None
    http_status: int | None = None
    protocol_code: str | None = None
    error_category: str | None = None
    retry_count: int = 0
    metadata: Mapping[str, str | int | float | bool] = field(
        default_factory=dict, repr=False
    )

    def __post_init__(self) -> None:
        if self.stage not in _VALID_STAGES:
            raise ValueError("collection attempt has an unsupported stage")
        if not isinstance(self.operation, str) or not self.operation.strip():
            raise ValueError("collection attempt operation must be non-empty text")
        if self.protocol not in {None, *_VALID_PROTOCOLS}:
            object.__setattr__(self, "protocol", None)
        operation = self.operation.strip()
        if operation not in _VALID_OPERATIONS or not _SAFE_OPERATION.fullmatch(operation) or any(
            marker in operation.casefold()
            for marker in ("://", "@", "password", "token", "authorization")
        ):
            object.__setattr__(self, "operation", "operation")
        else:
            object.__setattr__(self, "operation", operation)
        if self.outcome not in _VALID_OUTCOMES:
            raise ValueError("collection attempt has an unsupported outcome")
        if type(self.duration) not in {float, int} or not isfinite(float(self.duration)):
            raise ValueError("collection attempt duration must be finite")
        if self.duration < 0:
            raise ValueError("collection attempt duration cannot be negative")
        if self.http_status is not None and (
            type(self.http_status) is not int or not 100 <= self.http_status <= 599
        ):
            raise ValueError("HTTP status must be between 100 and 599")
        if type(self.retry_count) is not int or self.retry_count < 0:
            raise ValueError("retry_count must be a non-negative integer")
        if self.error_category is not None and self.error_category not in _VALID_ERROR_CATEGORIES:
            raise ValueError("collection attempt has an unsupported normalized error category")
        if self.protocol_code is not None and not _SAFE_CODE.fullmatch(self.protocol_code):
            object.__setattr__(self, "protocol_code", None)
        if self.authentication_mechanism not in {
            None,
            "NONE",
            "HTTP_BASIC",
            "HTTP_DIGEST",
            "WS_SECURITY_USERNAME_TOKEN",
            "UNKNOWN",
        }:
            object.__setattr__(self, "authentication_mechanism", "UNKNOWN")
        object.__setattr__(self, "metadata", self._safe_metadata(self.metadata))

    @staticmethod
    def _safe_metadata(
        metadata: Mapping[str, object],
    ) -> Mapping[str, str | int | float | bool]:
        safe: dict[str, str | int | float | bool] = {}
        if not isinstance(metadata, Mapping):
            return MappingProxyType(safe)
        for key, value in metadata.items():
            normalized_key = str(key).casefold()
            if normalized_key not in _SAFE_METADATA_KEYS:
                continue
            if isinstance(value, bool) or type(value) is int or (
                type(value) is float and isfinite(value)
            ):
                safe[normalized_key] = value
            elif isinstance(value, str) and len(value) <= 80:
                folded = value.casefold()
                if not any(
                    marker in folded
                    for marker in ("://", "@", "password", "token", "authorization")
                ):
                    safe[normalized_key] = value
        return MappingProxyType(safe)


@dataclass(frozen=True, slots=True)
class CollectionReport:
    """Monotonic aggregate and source of truth for a single collection."""

    evidence: tuple[EvidenceRecord, ...] = ()
    attempts: tuple[CollectionAttempt, ...] = ()
    required_fields: tuple[str, ...] = _IDENTITY_FIELDS
    cancelled: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence", tuple(self.evidence))
        object.__setattr__(self, "attempts", tuple(self.attempts))
        object.__setattr__(self, "required_fields", tuple(dict.fromkeys(self.required_fields)))
        if any(not isinstance(item, EvidenceRecord) for item in self.evidence):
            raise TypeError("report evidence must contain EvidenceRecord values")
        if any(not isinstance(item, CollectionAttempt) for item in self.attempts):
            raise TypeError("report attempts must contain CollectionAttempt values")
        if self.required_fields != _IDENTITY_FIELDS:
            raise ValueError("CollectionReport currently implements only IDENTITY_V1")
        if type(self.cancelled) is not bool:
            raise ValueError("cancelled must be a boolean")

    @property
    def provenance(self) -> tuple[tuple[str, tuple[EvidenceRecord, ...]], ...]:
        fields = sorted({item.field for item in self.evidence})
        return tuple(
            (name, tuple(item for item in self.evidence if item.field == name)) for name in fields
        )

    @property
    def conflicts(self) -> tuple[str, ...]:
        return tuple(
            name
            for name, records in self.provenance
            if len({self._comparison_value(name, item.value) for item in records}) > 1
        )

    @property
    def conflict_records(self) -> tuple[tuple[str, tuple[EvidenceRecord, ...]], ...]:
        return tuple((name, records) for name, records in self.provenance if name in self.conflicts)

    @property
    def coverage(self) -> Mapping[str, bool]:
        return MappingProxyType(
            {name: self._required_value(name) is not None for name in self.required_fields}
        )

    @property
    def missing_fields(self) -> tuple[str, ...]:
        return tuple(name for name in self.required_fields if not self.coverage[name])

    @property
    def status(self) -> CollectionStatus:
        if self.cancelled or any(item.outcome == "CANCELLED" for item in self.attempts):
            return CollectionStatus.CANCELLED
        if not self.missing_fields and not any(
            name in self.conflicts for name in self.required_fields
        ):
            return CollectionStatus.SUCCESS
        if any(
            item.field in _USEFUL_EVIDENCE_FIELDS
            and (item.field != "manufacturer" or item.confidence == "STRONG")
            for item in self.evidence
        ):
            return CollectionStatus.PARTIAL_SUCCESS
        if any(name in self.conflicts for name in _IDENTITY_FIELDS):
            return CollectionStatus.PARTIAL_SUCCESS
        return CollectionStatus.FAILED

    def values_for(self, field_name: str) -> tuple[str, ...]:
        """Return deterministic distinct values without discarding conflicting evidence."""
        by_comparison: dict[str, list[EvidenceRecord]] = {}
        for item in self.evidence:
            if item.field == field_name:
                by_comparison.setdefault(
                    self._comparison_value(field_name, item.value), []
                ).append(item)
        return tuple(
            min(records, key=self._record_rank).value
            for _, records in sorted(by_comparison.items())
        )

    def value_for(self, field_name: str, *, require_strong: bool = False) -> str | None:
        records = [item for item in self.evidence if item.field == field_name]
        if require_strong:
            records = [item for item in records if item.confidence == "STRONG"]
        if not records or field_name in self.conflicts:
            return None
        return min(records, key=self._record_rank).value

    def merged(self, other: CollectionReport) -> CollectionReport:
        """Append evidence and attempts; no write can erase an earlier valid value."""
        if self.required_fields != other.required_fields:
            required = tuple(dict.fromkeys((*self.required_fields, *other.required_fields)))
        else:
            required = self.required_fields
        return CollectionReport(
            evidence=self.evidence + other.evidence,
            attempts=self.attempts + other.attempts,
            required_fields=required,
            cancelled=self.cancelled or other.cancelled,
        )

    def with_attempt(self, attempt: CollectionAttempt) -> CollectionReport:
        return replace(self, attempts=self.attempts + (attempt,))

    def with_evidence(self, *records: EvidenceRecord) -> CollectionReport:
        return replace(self, evidence=self.evidence + tuple(records))

    def validated_for_target(self, sensitive_values: tuple[str, ...]) -> CollectionReport:
        """Apply target-scoped secret checks before reports cross an application boundary."""
        safe_evidence = tuple(
            item
            for item in self.evidence
            if is_valid_evidence_value(
                item.field, item.value, sensitive_values=sensitive_values
            )
        )
        if len(safe_evidence) == len(self.evidence):
            return self
        return replace(
            self,
            evidence=safe_evidence,
            attempts=self.attempts
            + (
                CollectionAttempt(
                    stage="PARSE",
                    operation="parse_device_information",
                    outcome="FAILED",
                    error_category="INVALID_RESPONSE",
                ),
            ),
        )

    def to_camera_result(self, ip: str, *, duration: float = 0.0) -> CameraResult:
        status = self.status
        error_attempt = self._primary_error_attempt()
        error_code = (
            _error_code_for_category(error_attempt.error_category)
            if error_attempt is not None
            and status not in {CollectionStatus.SUCCESS, CollectionStatus.CANCELLED}
            else None
        )
        error_message: str | None = None
        if status is CollectionStatus.CANCELLED:
            error_message = "Coleta cancelada; as evidências obtidas foram preservadas."
        elif status is CollectionStatus.FAILED:
            error_message = self._failure_message(error_attempt)
            error_code = error_code or ErrorCode.ONVIF_ERROR
        elif status is CollectionStatus.PARTIAL_SUCCESS:
            error_message = self._partial_message(error_attempt)

        manufacturer = self.value_for("manufacturer", require_strong=True)
        fields_by_name = {
            "hostname": self.value_for("hostname"),
            "manufacturer": manufacturer,
            "manufacturer_original": self.value_for("manufacturer_original"),
            "model": self.value_for("model"),
            "serial": self.value_for("serial"),
            "firmware": self.value_for("firmware"),
            "hardware_id": self.value_for("hardware_id"),
            "mac": self.value_for("mac"),
        }
        protocols = {
            item.protocol for item in (*self.attempts, *self.evidence) if item.protocol is not None
        }
        has_onvif = "ONVIF" in protocols
        vendor_operations = {
            "GET /ISAPI/System/deviceInfo",
            "POST /axis-cgi/basicdeviceinfo.cgi getAllProperties",
            "GET /stw-cgi/system.cgi deviceinfo view",
            "GET /cgi-bin/magicBox.cgi getSystemInfo",
            "GET /cgi-bin/magicBox.cgi getVendor",
            "GET /cgi-bin/getinfo",
        }
        vendor_records = (*self.evidence, *self.attempts)
        has_vendor_http = any(
            item.protocol in {"HTTP", "HTTPS"}
            and item.operation in vendor_operations
            and (not isinstance(item, CollectionAttempt) or item.outcome == "SUCCESS")
            for item in vendor_records
        )
        has_hikvision_http = any(
            item.protocol in {"HTTP", "HTTPS"}
            and item.operation == "GET /ISAPI/System/deviceInfo"
            and (not isinstance(item, CollectionAttempt) or item.outcome == "SUCCESS")
            for item in vendor_records
        )
        method = (
            CollectionMethod.HYBRID
            if has_onvif and has_vendor_http
            else CollectionMethod.HIKVISION_ISAPI
            if has_hikvision_http
            else CollectionMethod.VENDOR_HTTP
            if has_vendor_http
            else CollectionMethod.ONVIF
            if has_onvif
            else None
        )
        return CameraResult(
            ip=self._safe_ip(ip),
            status=status,
            **fields_by_name,
            error_code=error_code,
            error_message=error_message,
            collection_method=method,
            duration=float(duration),
        )

    @classmethod
    def from_camera_result(
        cls,
        result: CameraResult,
        *,
        source: str = "LEGACY",
        sensitive_values: tuple[str, ...] = (),
    ) -> CollectionReport:
        evidence: list[EvidenceRecord] = []
        rejected_value = False
        for name in (
            "hostname",
            "manufacturer",
            "manufacturer_original",
            "model",
            "serial",
            "firmware",
            "hardware_id",
            "mac",
        ):
            value = getattr(result, name)
            if is_valid_evidence_value(name, value, sensitive_values=sensitive_values):
                evidence.append(
                    EvidenceRecord(
                        field=name,
                        value=value,
                        source=source,
                        confidence="STRONG",
                        protocol=(
                            result.collection_method.value
                            if result.collection_method
                            else None
                        ),
                        operation=(
                            "GetDeviceInformation"
                            if result.collection_method is CollectionMethod.ONVIF
                            else None
                        ),
                    )
                )
            elif value is not None:
                rejected_value = True
        attempts: list[CollectionAttempt] = []
        if rejected_value:
            attempts.append(
                CollectionAttempt(
                    stage="PARSE",
                    operation="parse_device_information",
                    protocol=(
                        result.collection_method.value if result.collection_method else None
                    ),
                    outcome="FAILED",
                    error_category="INVALID_RESPONSE",
                )
            )
        if result.error_code is not None and result.status is not CollectionStatus.SUCCESS:
            category = {
                ErrorCode.TIMEOUT: "READ_TIMEOUT",
                ErrorCode.NETWORK_ERROR: "CONNECTION_REFUSED",
                ErrorCode.AUTH_ERROR: "AUTH_REJECTED",
                ErrorCode.ONVIF_ERROR: "SOAP_FAULT",
                ErrorCode.INVALID_INPUT: "INVALID_INPUT",
                ErrorCode.UNEXPECTED_ERROR: "UNEXPECTED",
            }.get(result.error_code, "UNEXPECTED")
            attempts.append(
                CollectionAttempt(
                    stage=(
                        "SOAP"
                        if result.collection_method is CollectionMethod.ONVIF
                        else "VALIDATE"
                    ),
                    operation=(
                        "GetDeviceInformation"
                        if result.collection_method is CollectionMethod.ONVIF
                        else "collect"
                    ),
                    protocol=result.collection_method.value if result.collection_method else None,
                    outcome="FAILED",
                    error_category=category,
                    duration=result.duration,
                )
            )
        return cls(
            evidence=tuple(evidence),
            attempts=tuple(attempts),
            cancelled=result.status is CollectionStatus.CANCELLED,
        )

    @staticmethod
    def _comparison_value(field_name: str, value: str) -> str:
        folded = " ".join(value.split()).casefold()
        if field_name == "manufacturer":
            return {
                "axis communications": "axis",
                "hik": "hikvision",
                "samsung": "samsung/hanwha",
                "samsung techwin": "samsung/hanwha",
                "hanwha": "samsung/hanwha",
            }.get(folded, folded)
        return folded

    @staticmethod
    def _safe_ip(value: str) -> str:
        try:
            return str(ipaddress.ip_address(value))
        except (ValueError, TypeError):
            return "<invalid>"

    @staticmethod
    def _record_rank(record: EvidenceRecord) -> tuple[int, str, str, str, str]:
        return (
            0 if record.confidence == "STRONG" else 1,
            record.source.casefold(),
            (record.operation or "").casefold(),
            record.value.casefold(),
            record.value,
        )

    def _required_value(self, name: str) -> str | None:
        return self.value_for(name, require_strong=name == "manufacturer")

    def _primary_error_attempt(self) -> CollectionAttempt | None:
        errors = [item for item in self.attempts if item.error_category is not None]
        if not errors:
            return None
        ranks = {
            "AUTH_REJECTED": 0,
            "AUTHORIZATION_DENIED": 0,
            "AUTH_MECHANISM_UNSUPPORTED": 1,
            "READ_TIMEOUT": 2,
            "CONNECT_TIMEOUT": 2,
            "DEADLINE_EXCEEDED": 2,
            "TLS_ERROR": 3,
            "CONNECTION_REFUSED": 3,
            "ENDPOINT_UNSUPPORTED": 4,
            "SOAP_FAULT": 5,
            "INVALID_RESPONSE": 5,
            "HTTP_ERROR": 6,
            "UNEXPECTED": 7,
            "INVALID_INPUT": 8,
        }
        return min(
            errors,
            key=lambda item: (ranks.get(item.error_category or "", 9), item.operation),
        )

    def _failure_message(self, attempt: CollectionAttempt | None) -> str:
        if attempt is None:
            return "Nenhuma evidência útil de identidade foi obtida."
        public_message = {
            ErrorCode.TIMEOUT: "A consulta excedeu o tempo limite.",
            ErrorCode.NETWORK_ERROR: "Não foi possível conectar à câmera.",
            ErrorCode.AUTH_ERROR: "A câmera recusou a autenticação.",
            ErrorCode.ONVIF_ERROR: "A câmera retornou um erro ONVIF.",
            ErrorCode.INVALID_INPUT: "Dados inválidos. Verifique o endereço IP e o usuário.",
            ErrorCode.UNEXPECTED_ERROR: "Ocorreu um erro inesperado durante a consulta.",
        }[_error_code_for_category(attempt.error_category or "UNEXPECTED")]
        return public_message

    def _partial_message(self, attempt: CollectionAttempt | None) -> str:
        parts: list[str] = []
        if any(item.source == "ONVIF_PREAUTH" for item in self.evidence):
            parts.append(
                "A câmera forneceu evidência pré-autenticação, mas a identidade está incompleta."
            )
        if self.conflicts:
            parts.append("Conflito de evidência em " + ", ".join(self.conflicts) + ".")
        if self.missing_fields:
            parts.append("Campos de identidade ausentes: " + ", ".join(self.missing_fields) + ".")
        if attempt is not None:
            parts.append(f"Falha em {attempt.operation}: {attempt.error_category}.")
        return " ".join(parts) or "Identidade incompleta; evidência parcial preservada."


@dataclass(frozen=True, slots=True)
class CameraResult:
    """Sanitized camera output. This model intentionally has no password field."""

    ip: str
    status: CollectionStatus
    hostname: str | None = None
    manufacturer: str | None = None
    manufacturer_original: str | None = None
    model: str | None = None
    serial: str | None = None
    firmware: str | None = None
    hardware_id: str | None = None
    mac: str | None = None
    error_code: ErrorCode | None = None
    error_message: str | None = None
    collection_method: CollectionMethod | None = None
    duration: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.status, CollectionStatus):
            raise TypeError("status must use CollectionStatus")
        if self.error_code is not None and not isinstance(self.error_code, ErrorCode):
            raise TypeError("error_code must use ErrorCode")
        if self.error_message is not None and not isinstance(self.error_message, str):
            raise TypeError("error_message must be text")
        if self.collection_method is not None and not isinstance(
            self.collection_method, CollectionMethod
        ):
            raise TypeError("collection_method must use CollectionMethod")
        if type(self.duration) is not float:
            raise TypeError("duration must be a float")
        if not isfinite(self.duration) or self.duration < 0:
            raise ValueError("duration must be a finite float greater than or equal to zero")
        if self.status is CollectionStatus.SUCCESS and (
            self.error_code is not None or self.error_message is not None
        ):
            raise ValueError("successful results cannot contain error details")
        if self.status is CollectionStatus.FAILED and (
            self.error_code is None
            or not isinstance(self.error_message, str)
            or not self.error_message.strip()
        ):
            raise ValueError("failed results require an error code and message")
