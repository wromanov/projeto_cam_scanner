"""Generic, read-only ONVIF collection for the P1 device information operation."""
from __future__ import annotations

import logging
import time
from collections.abc import Callable, Mapping
from typing import Any

from cam_scanner.cameras.collector import CameraCollector
from cam_scanner.cameras.manufacturer import ManufacturerNormalizer
from cam_scanner.cameras.transport import ControlledOnvifClient
from cam_scanner.domain.errors import normalize_collection_error
from cam_scanner.domain.models import (
    CameraResult,
    CameraTarget,
    CollectionAttempt,
    CollectionReport,
    EvidenceRecord,
    is_valid_evidence_value,
)


class GenericOnvifCollector(CameraCollector):
    """Read P1 device information and retain sanitized diagnostics on every path."""

    def __init__(
        self,
        client_factory: Callable[..., Any] | None = None,
        timeout_seconds: int = 7,
    ) -> None:
        self._client_factory = client_factory
        self._timeout_seconds = timeout_seconds
        self._manufacturer_normalizer = ManufacturerNormalizer()

    def collect(self, target: CameraTarget, *, context: Any = None) -> CameraResult:
        return self.collect_report(target, context=context).to_camera_result(target.ip)

    def collect_report(self, target: CameraTarget, *, context: Any = None) -> CollectionReport:
        _suppress_dependency_logs()
        client_factory = self._client_factory
        client_options: dict[str, object] = {
            "host": target.ip,
            "port": 80,
            "username": target.username,
            "password": target.password,
            "timeout": self._timeout_seconds,
        }
        if client_factory is None and context is None:
            return CollectionReport().with_attempt(self._failed_attempt(
                ValueError("context required"), "CONNECT", "create_onvif_client", time.monotonic()
            ))

        report = CollectionReport()
        started = time.monotonic()
        try:
            if context is not None:
                context.check("ONVIF")
            client = (ControlledOnvifClient(context, authenticated=True)
                      if client_factory is None else client_factory(**client_options))
            device_service = client.devicemgmt()
        except KeyboardInterrupt:
            return report.with_attempt(
                CollectionAttempt(
                    stage="CONNECT",
                    operation="create_onvif_client",
                    protocol="ONVIF",
                    outcome="CANCELLED",
                    duration=self._elapsed(started),
                )
            )
        except Exception as exception:  # noqa: BLE001 - no raw exception enters the report.
            return report.with_attempt(
                self._failed_attempt(exception, "CONNECT", "create_onvif_client", started)
            )

        started = time.monotonic()
        try:
            if context is not None:
                context.check("ONVIF")
            device_info = device_service.GetDeviceInformation()
        except KeyboardInterrupt:
            return report.with_attempt(
                CollectionAttempt(
                    stage="SOAP",
                    operation="GetDeviceInformation",
                    protocol="ONVIF",
                    authentication_mechanism="WS_SECURITY_USERNAME_TOKEN",
                    outcome="CANCELLED",
                    duration=self._elapsed(started),
                )
            )
        except Exception as exception:  # noqa: BLE001 - classify without storing exception text.
            category, _, _ = normalize_collection_error(
                exception, stage="SOAP", authenticated=True
            )
            return report.with_attempt(
                self._failed_attempt(
                    exception,
                    self._stage_for(category),
                    "GetDeviceInformation",
                    started,
                )
            )

        report = report.with_attempt(
            CollectionAttempt(
                stage="SOAP",
                operation="GetDeviceInformation",
                protocol="ONVIF",
                authentication_mechanism="WS_SECURITY_USERNAME_TOKEN",
                outcome="SUCCESS",
                duration=self._elapsed(started),
            )
        )
        started = time.monotonic()
        try:
            secrets = (target.username, target.password)
            raw_fields = {
                "manufacturer": self._raw_field(device_info, "Manufacturer"),
                "model": self._raw_field(device_info, "Model"),
                "serial": self._raw_field(device_info, "SerialNumber"),
                "firmware": self._raw_field(device_info, "FirmwareVersion"),
            }
            rejected_fields = [
                name
                for name, raw_value in raw_fields.items()
                if raw_value is not None
                and not is_valid_evidence_value(
                    name, raw_value, sensitive_values=secrets
                )
            ]
            raw_manufacturer = raw_fields["manufacturer"]
            if not isinstance(raw_manufacturer, str) or not is_valid_evidence_value(
                "manufacturer", raw_manufacturer, sensitive_values=secrets
            ):
                raw_manufacturer = None
            safe_raw_manufacturer = self._safe_original_manufacturer(raw_manufacturer, secrets)
            manufacturer = self._manufacturer_normalizer.normalize(
                safe_raw_manufacturer
            )
            records: list[EvidenceRecord] = []
            values = {
                "manufacturer": manufacturer,
                "manufacturer_original": safe_raw_manufacturer,
                "model": raw_fields["model"]
                if is_valid_evidence_value("model", raw_fields["model"], sensitive_values=secrets)
                else None,
                "serial": raw_fields["serial"]
                if is_valid_evidence_value("serial", raw_fields["serial"], sensitive_values=secrets)
                else None,
                "firmware": raw_fields["firmware"]
                if is_valid_evidence_value("firmware", raw_fields["firmware"], sensitive_values=secrets)
                else None,
            }
            for name, value in values.items():
                if is_valid_evidence_value(name, value):
                    records.append(
                        EvidenceRecord(
                            field=name,
                            value=(
                                value
                                if name == "manufacturer_original"
                                else " ".join(value.split())
                            ),
                            source="ONVIF_AUTHENTICATED",
                            confidence="STRONG",
                            protocol="ONVIF",
                            operation="GetDeviceInformation",
                        )
                    )
        except Exception as exception:  # noqa: BLE001
            return report.with_attempt(
                self._failed_attempt(exception, "PARSE", "parse_device_information", started)
            )

        report = report.with_evidence(*records)
        if rejected_fields:
            report = report.with_attempt(
                CollectionAttempt(
                    stage="PARSE",
                    operation="parse_device_information",
                    protocol="ONVIF",
                    outcome="FAILED",
                    duration=self._elapsed(started),
                    error_category="INVALID_RESPONSE",
                )
            )
            return report
        return report.with_attempt(
            CollectionAttempt(
                stage="PARSE",
                operation="parse_device_information",
                protocol="ONVIF",
                outcome="SUCCESS",
                duration=self._elapsed(started),
            )
        )

    @classmethod
    def _failed_attempt(
        cls, exception: Exception, stage: str, operation: str, started: float
    ) -> CollectionAttempt:
        category, http_status, protocol_code = normalize_collection_error(
            exception, stage=stage,
            authenticated=operation == "GetDeviceInformation",
        )
        return CollectionAttempt(
            stage=cls._stage_for(category) if stage in {"CONNECT", "SOAP"} else stage,
            operation=operation,
            protocol="ONVIF",
            outcome="FAILED",
            duration=cls._elapsed(started),
            authentication_mechanism=(
                "WS_SECURITY_USERNAME_TOKEN" if operation == "GetDeviceInformation" else None
            ),
            http_status=http_status,
            protocol_code=protocol_code,
            error_category=category,
        )

    @staticmethod
    def _stage_for(category: str) -> str:
        if category in {"CONNECT_TIMEOUT", "CONNECTION_REFUSED", "TLS_ERROR"}:
            return "CONNECT"
        if category in {"AUTH_REJECTED", "AUTHORIZATION_DENIED", "AUTH_MECHANISM_UNSUPPORTED"}:
            return "AUTH"
        if category in {"READ_TIMEOUT", "HTTP_ERROR", "ENDPOINT_UNSUPPORTED"}:
            return "HTTP"
        if category == "INVALID_RESPONSE":
            return "PARSE"
        return "SOAP"

    @staticmethod
    def _elapsed(started: float) -> float:
        return max(0.0, float(time.monotonic() - started))

    @staticmethod
    def _raw_field(device_info: object, name: str) -> object:
        if isinstance(device_info, Mapping):
            return device_info.get(name)
        return getattr(device_info, name, None)

    @staticmethod
    def _safe_original_manufacturer(
        value: str | None, sensitive_values: tuple[str, ...] = ()
    ) -> str | None:
        if (
            value is None
            or len(value) > 120
            or any(ord(character) < 32 for character in value)
            or not is_valid_evidence_value(
                "manufacturer_original", value, sensitive_values=sensitive_values
            )
        ):
            return None
        return value


def _suppress_dependency_logs() -> None:
    """Keep raw ONVIF/transport diagnostics from reaching terminal or log handlers."""
    for logger_name in ("onvif", "zeep", "requests", "urllib3"):
        dependency_logger = logging.getLogger(logger_name)
        dependency_logger.setLevel(logging.CRITICAL + 1)
        dependency_logger.propagate = False
