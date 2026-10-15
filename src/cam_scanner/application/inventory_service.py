"""Shared service for validated collection and one canonical aggregated report."""
from __future__ import annotations

import inspect
import ipaddress
import logging
import math
import threading
import time

from cam_scanner.application.collection_context import CollectionContext
from cam_scanner.cameras.collector import CameraCollector
from cam_scanner.config.models import EffectiveConfig
from cam_scanner.domain.enums import CollectionStatus
from cam_scanner.domain.errors import InvalidInputError, normalize_collection_error
from cam_scanner.domain.models import (
    CameraResult,
    CameraTarget,
    CollectionAttempt,
    CollectionReport,
)
from cam_scanner.logging.sanitize import sanitized_traceback


class InventoryService:
    """Validate each target and consolidate errors/evidence before public projection."""

    def __init__(
        self,
        collector: CameraCollector,
        logger: logging.Logger | None = None,
        *,
        config: object | None = None,
    ) -> None:
        self._collector = collector
        self._logger = logger or logging.getLogger("cam_scanner")
        self._config = config or EffectiveConfig()

    def create_context(
        self, target: CameraTarget, *, cancel_event: threading.Event | None = None
    ) -> CollectionContext:
        """Create the one per-row context before pre-auth and keep it through cleanup."""
        from cam_scanner.cameras.transport import TargetTransportPolicy

        return CollectionContext(
            target,
            self._config,
            cancel_event=cancel_event,
            transport_factory=TargetTransportPolicy,
        )

    def collect_execution(
        self,
        target: CameraTarget,
        *,
        context: CollectionContext | None = None,
        cancel_event: threading.Event | None = None,
    ) -> tuple[CollectionReport, CollectionContext]:
        """Collect into one context, returning it for snapshot and final cleanup."""
        execution_context = context or self.create_context(target, cancel_event=cancel_event)
        return self.collect_report(target, context=execution_context), execution_context

    def collect_one(self, target: CameraTarget) -> CameraResult:
        """P1-compatible public result; status and fields are projected from one report."""
        started_at = time.monotonic()
        try:
            self._validate_target(target)
        except InvalidInputError:
            report = self.collect_report(target)
        else:
            context = self.create_context(target)
            try:
                report = self.collect_report(target, context=context)
            finally:
                context.close()
        result = report.to_camera_result(target.ip, duration=self._duration_since(started_at))
        if report.status is CollectionStatus.FAILED:
            category = next(
                (item.error_category for item in reversed(report.attempts) if item.error_category),
                None,
            )
            if category is not None:
                self._log_failure(target, category, report)
        return result

    def collect_report(
        self, target: CameraTarget, *, context: CollectionContext | None = None
    ) -> CollectionReport:
        """Return the canonical aggregate used by SINGLE and the public result adapter."""
        started_at = time.monotonic()
        try:
            self._validate_target(target)
        except InvalidInputError:
            report = CollectionReport().with_attempt(
                CollectionAttempt(
                    stage="VALIDATE",
                    operation="validate_target",
                    outcome="FAILED",
                    duration=self._duration_since(started_at),
                    error_category="INVALID_INPUT",
                )
            )
            return context.merge(report) if context is not None else report

        report_method = getattr(self._collector, "collect_report", None)
        if callable(report_method):
            try:
                parameters = inspect.signature(report_method).parameters
                report = (
                    report_method(target, context=context)
                    if context is not None and "context" in parameters
                    else report_method(target)
                )
            except KeyboardInterrupt:
                cancelled = CollectionReport().with_attempt(
                    CollectionAttempt(
                        stage="MERGE",
                        operation="collect_one",
                        outcome="CANCELLED",
                        duration=self._duration_since(started_at),
                    )
                )
                return context.merge(cancelled) if context is not None else cancelled
            except Exception as exception:  # noqa: BLE001
                failed = self._exception_report(exception, target, started_at)
                return context.merge(failed) if context is not None else failed
            if isinstance(report, CollectionReport):
                validated = report.validated_for_target((target.username, target.password))
                return context.merge(validated) if context is not None else validated
            invalid_report = CollectionReport().with_attempt(
                CollectionAttempt(
                    stage="PARSE",
                    operation="collect_report",
                    outcome="FAILED",
                    duration=self._duration_since(started_at),
                    error_category="INVALID_RESPONSE",
                )
            )
            return context.merge(invalid_report) if context is not None else invalid_report

        try:
            result = self._collector.collect(target)
        except KeyboardInterrupt:
            cancelled = CollectionReport().with_attempt(
                CollectionAttempt(
                    stage="MERGE",
                    operation="collect_one",
                    outcome="CANCELLED",
                    duration=self._duration_since(started_at),
                )
            )
            return context.merge(cancelled) if context is not None else cancelled
        except Exception as exception:  # noqa: BLE001
            failed = self._exception_report(exception, target, started_at)
            return context.merge(failed) if context is not None else failed
        if not isinstance(result, CameraResult):
            invalid_result = CollectionReport().with_attempt(
                CollectionAttempt(
                    stage="PARSE",
                    operation="collect_result",
                    outcome="FAILED",
                    duration=self._duration_since(started_at),
                    error_category="INVALID_RESPONSE",
                )
            )
            return context.merge(invalid_result) if context is not None else invalid_result
        legacy_report = CollectionReport.from_camera_result(
            result,
            sensitive_values=(target.username, target.password),
        )
        return context.merge(legacy_report) if context is not None else legacy_report

    @staticmethod
    def _validate_target(target: CameraTarget) -> None:
        if not isinstance(target, CameraTarget):
            raise InvalidInputError("Target must use CameraTarget")
        if not isinstance(target.ip, str):
            raise InvalidInputError("Target IP must be text")
        try:
            ipaddress.ip_address(target.ip)
        except (ValueError, TypeError) as exception:
            raise InvalidInputError("Target IP must be a valid IPv4 or IPv6 address") from exception
        if not isinstance(target.username, str) or not target.username.strip():
            raise InvalidInputError("Target username cannot be empty")
        if not isinstance(target.password, str):
            raise InvalidInputError("Target password must be text")

    def _exception_report(
        self, exception: Exception, target: CameraTarget, started_at: float
    ) -> CollectionReport:
        category, http_status, protocol_code = normalize_collection_error(exception, stage="SOAP")
        stage = self._stage_for(category)
        attempt = CollectionAttempt(
            stage=stage,
            operation="collect_one",
            protocol="ONVIF",
            outcome="FAILED",
            duration=self._duration_since(started_at),
            http_status=http_status,
            protocol_code=protocol_code,
            error_category=category,
        )
        if category == "UNEXPECTED":
            self._log_unexpected(target, exception)
        return CollectionReport().with_attempt(attempt)

    @staticmethod
    def _duration_since(started_at: float) -> float:
        elapsed = float(time.monotonic() - started_at)
        if not math.isfinite(elapsed):
            return 0.0
        return max(0.0, elapsed)

    @staticmethod
    def _stage_for(category: str) -> str:
        if category in {"CONNECT_TIMEOUT", "CONNECTION_REFUSED", "TLS_ERROR"}:
            return "CONNECT"
        if category in {"AUTH_REJECTED", "AUTHORIZATION_DENIED", "AUTH_MECHANISM_UNSUPPORTED"}:
            return "AUTH"
        if category in {"READ_TIMEOUT", "HTTP_ERROR", "ENDPOINT_UNSUPPORTED"}:
            return "HTTP"
        if category == "SOAP_FAULT":
            return "SOAP"
        if category == "INVALID_RESPONSE":
            return "PARSE"
        return "MERGE"

    def _log_failure(
        self, target: CameraTarget, category: str, report: CollectionReport
    ) -> None:
        safe_ip = target.ip
        try:
            ipaddress.ip_address(target.ip)
        except ValueError:
            safe_ip = "<invalid>"
        self._logger.warning(
            "Camera collection failed: ip=%s error_category=%s attempts=%d",
            safe_ip,
            category,
            len(report.attempts),
        )

    def _log_unexpected(self, target: CameraTarget, exception: Exception) -> None:
        self._logger.warning("Camera collection failed: ip=%s error_category=UNEXPECTED", target.ip)
        diagnostic = sanitized_traceback(
            exception,
            exception.__traceback__,
            sensitive_values=(target.password, target.username),
        )
        self._logger.error("Unexpected collection diagnostic (sanitized):\n%s", diagnostic)
