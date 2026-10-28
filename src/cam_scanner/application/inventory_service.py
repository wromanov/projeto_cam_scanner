"""Shared service for validated collection and one canonical aggregated report."""
from __future__ import annotations

import inspect
import ipaddress
import logging
import math
import threading
import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from cam_scanner.application.collection_context import CollectionContext
from cam_scanner.cameras.collector import CameraCollector
from cam_scanner.config.models import EffectiveConfig
from cam_scanner.config.transport_plan import select_transport
from cam_scanner.domain.enums import CollectionStatus
from cam_scanner.domain.errors import (
    ConfigurationError,
    InvalidInputError,
    normalize_collection_error,
)
from cam_scanner.domain.models import (
    CameraResult,
    CameraTarget,
    CollectionAttempt,
    CollectionReport,
    ModelHint,
    parse_model_hint,
)
from cam_scanner.logging.sanitize import sanitized_traceback


@dataclass(frozen=True, slots=True)
class TransportInputDescriptor:
    """Non-secret row fields needed to summarize and freeze a transport choice."""

    row_id: int
    ip: str
    valid: bool
    manufacturer_hint: str | None = None
    model_hint: ModelHint | None = None


@dataclass(frozen=True, slots=True)
class TransportSelectionOption:
    """Safe per-execution summary; never contains a credential or target list."""

    selection_id: str = field(repr=False)
    authorization_ref: str | None = field(repr=False)
    auth_mode: str
    http_rows: int
    https_rows: int
    ineligible_rows: int
    available: bool = True


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
        self,
        target: CameraTarget,
        *,
        cancel_event: threading.Event | None = None,
        manufacturer_hint: str | None = None,
        model_hint: ModelHint | str | None = None,
        transport_config: object | None = None,
        transport_selection_id: str = "HTTPS_DEFAULT",
        transport_selection_metadata: Mapping[str, str | None] | None = None,
        transport_selection_blocked: bool = False,
    ) -> CollectionContext:
        """Create the one per-row context before pre-auth and keep it through cleanup."""
        from cam_scanner.cameras.transport import TargetTransportPolicy

        effective_config = transport_config if transport_config is not None else self._config
        if isinstance(effective_config, EffectiveConfig) and effective_config.transport_plan is None:
            component = _vendor_component(manufacturer_hint)
            known_components = {target.ip: component} if component is not None else {}
            if _is_canonical_ip(target.ip):
                effective_config = select_transport(
                    effective_config,
                    (target.ip,),
                    known_components,
                    "HTTPS_DEFAULT",
                )
        safe_model_hint = (
            parse_model_hint(
                model_hint.declared,
                sensitive_values=(target.username, target.password),
            )
            if isinstance(model_hint, ModelHint)
            else parse_model_hint(
                model_hint,
                sensitive_values=(target.username, target.password),
            )
        )
        context = CollectionContext(
            target,
            effective_config,
            cancel_event=cancel_event,
            transport_factory=TargetTransportPolicy,
            manufacturer_hint=manufacturer_hint,
            model_hint=safe_model_hint,
        )
        context.model_hint_invalid = model_hint is not None and safe_model_hint is None
        context.transport_selection_id = transport_selection_id
        context.transport_selection_metadata = dict(transport_selection_metadata or {})
        context.transport_selection_blocked = bool(transport_selection_blocked)
        return context

    def transport_selection_options(
        self, rows: Iterable[TransportInputDescriptor]
    ) -> tuple[TransportSelectionOption, ...]:
        """Summarize configured choices using only validated IP/manufacturer declarations."""
        materialized = tuple(row for row in rows if row.valid)
        options = [TransportSelectionOption(
            "HTTPS_DEFAULT", None, "NONE", 0, len(materialized), 0, True
        )]
        config = self._config
        if not isinstance(config, EffectiveConfig):
            return tuple(options)
        for profile in config.transport_profiles:
            in_group = [row for row in materialized if row.ip in profile.targets]
            eligible = sum(
                _vendor_component(row.manufacturer_hint) == profile.component
                and _transport_model_eligible(profile.component, row.model_hint)
                for row in in_group
            )
            ineligible = len(in_group) - eligible
            options.append(TransportSelectionOption(
                profile.id,
                profile.authorization_ref,
                profile.auth_mode,
                eligible,
                len(materialized) - len(in_group),
                ineligible,
                eligible > 0,
            ))
        legacy_http = tuple(rule for rule in config.transport_rules if rule.protocol == "http")
        if legacy_http:
            targets = {rule.target for rule in legacy_http}
            eligible = sum(
                any(row.ip == rule.target and _vendor_component(row.manufacturer_hint) == rule.component
                    for rule in legacy_http)
                for row in materialized
            )
            in_group = sum(row.ip in targets for row in materialized)
            options.append(TransportSelectionOption(
                "LEGACY_EXACT", None, "EXISTING", eligible,
                len(materialized) - in_group, in_group - eligible, False,
            ))
        return tuple(options)

    def prepare_transport_for_row(
        self,
        ip: str,
        manufacturer_hint: str | None,
        selection_id: str,
        *,
        model_hint: ModelHint | str | None = None,
    ) -> tuple[object, bool, dict[str, str | None]]:
        """Compile the immutable per-row plan before scheduling any collection work."""
        config = self._config
        if not isinstance(config, EffectiveConfig):
            return config, False, _selection_metadata(selection_id)
        if not _is_canonical_ip(ip):
            return config, False, _selection_metadata(selection_id)
        component = _vendor_component(manufacturer_hint)
        safe_model_hint = (
            model_hint if isinstance(model_hint, ModelHint) else parse_model_hint(model_hint)
        )
        known_components = {ip: component} if component is not None else {}
        profile = next((item for item in config.transport_profiles
                        if item.id == selection_id), None)
        metadata = _selection_metadata(selection_id)
        blocked = False
        if profile is not None:
            if ip not in profile.targets:
                effective = select_transport(
                    config, (ip,), known_components, "HTTPS_DEFAULT"
                )
                return effective, False, _selection_metadata("HTTPS_DEFAULT")
            metadata = {
                "policy_id": profile.id,
                "authorization_ref": profile.authorization_ref,
                "auth_mode": profile.auth_mode,
            }
            if (component != profile.component
                    or not _transport_model_eligible(profile.component, safe_model_hint)):
                blocked = True
                effective = select_transport(config, (ip,), {}, "HTTPS_DEFAULT")
                return effective, blocked, metadata
            selected = selection_id
        elif selection_id == "LEGACY_EXACT":
            raise ConfigurationError(
                "Regra HTTP legada sem referência de autorização e aceite vinculados."
            )
        elif selection_id == "HTTPS_DEFAULT":
            selected = selection_id
        else:
            raise ConfigurationError("Seleção de transporte desconhecida.")
        effective = select_transport(config, (ip,), known_components, selected)
        return effective, blocked, metadata

    def collect_execution(
        self,
        target: CameraTarget,
        *,
        context: CollectionContext | None = None,
        cancel_event: threading.Event | None = None,
        manufacturer_hint: str | None = None,
        model_hint: ModelHint | str | None = None,
        transport_config: object | None = None,
        transport_selection_id: str = "HTTPS_DEFAULT",
        transport_selection_metadata: Mapping[str, str | None] | None = None,
        transport_selection_blocked: bool = False,
    ) -> tuple[CollectionReport, CollectionContext]:
        """Collect into one context, returning it for snapshot and final cleanup."""
        if context is not None:
            execution_context = context
        else:
            create_context_options: dict[str, object] = {
                "cancel_event": cancel_event,
                "manufacturer_hint": manufacturer_hint,
                "transport_config": transport_config,
                "transport_selection_id": transport_selection_id,
                "transport_selection_metadata": transport_selection_metadata,
                "transport_selection_blocked": transport_selection_blocked,
            }
            try:
                create_context_parameters = inspect.signature(self.create_context).parameters
            except (TypeError, ValueError):
                create_context_parameters = {}
            accepts_kwargs = any(
                parameter.kind is inspect.Parameter.VAR_KEYWORD
                for parameter in create_context_parameters.values()
            )
            if "model_hint" in create_context_parameters or accepts_kwargs:
                create_context_options["model_hint"] = model_hint
            if not accepts_kwargs and create_context_parameters:
                create_context_options = {
                    key: value for key, value in create_context_options.items()
                    if key in create_context_parameters
                }
            execution_context = self.create_context(target, **create_context_options)
        if not getattr(execution_context, "transport_selection_recorded", False):
            metadata = dict(getattr(execution_context, "transport_selection_metadata", {}))
            metadata.setdefault(
                "policy_id", getattr(execution_context, "transport_selection_id", "HTTPS_DEFAULT")
            )
            metadata.setdefault(
                "auth_mode",
                "NONE" if metadata["policy_id"] == "HTTPS_DEFAULT" else "EXISTING",
            )
            metadata = _safe_selection_metadata(
                metadata, (target.username, target.password)
            )
            execution_context.merge(CollectionReport().with_attempt(CollectionAttempt(
                stage="CONNECT", operation="select_transport_policy",
                outcome=(
                    "CANCELLED"
                    if getattr(execution_context, "cancel_event", None)
                    and execution_context.cancel_event.is_set()
                    else "SKIPPED"
                ),
                metadata=metadata,
            )))
            execution_context.transport_selection_recorded = True
        report = (
            execution_context.report
            if getattr(execution_context, "transport_selection_blocked", False)
            else self.collect_report(target, context=execution_context)
        )
        hint = getattr(execution_context, "model_hint", None)
        if hint is not None:
            report = report.with_model_hint(hint)
        invalid_hint = model_hint is not None and hint is None
        if invalid_hint:
            execution_context.model_hint_invalid = True
        if invalid_hint or getattr(execution_context, "model_hint_invalid", False):
            report = report.with_attempt(CollectionAttempt(
                stage="VALIDATE", operation="validate_model_hint", outcome="FAILED",
                error_category="INVALID_INPUT",
            ))
        return report, execution_context

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
                report, _ = self.collect_execution(target, context=context)
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
                if context is not None:
                    context.cancel_event.set()
                cancelled = CollectionReport(cancelled=True).with_attempt(
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
            if context is not None:
                context.cancel_event.set()
            cancelled = CollectionReport(cancelled=True).with_attempt(
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


def _vendor_component(manufacturer_hint: str | None) -> str | None:
    if not isinstance(manufacturer_hint, str):
        return None
    normalized = manufacturer_hint.strip().casefold().replace("/", " ").replace("-", " ")
    for marker, component in (
        ("axis", "vendor_axis"),
        ("hikvision", "vendor_hikvision"),
        ("dahua", "vendor_dahua"),
        ("panasonic", "vendor_panasonic"),
        ("i pro", "vendor_panasonic"),
        ("hanwha", "vendor_hanwha"),
        ("samsung", "vendor_hanwha"),
    ):
        if marker in normalized:
            return component
    return None


def _is_canonical_ip(value: object) -> bool:
    if type(value) is not str:
        return False
    try:
        return ipaddress.ip_address(value).compressed == value
    except ValueError:
        return False


def _selection_metadata(selection_id: str) -> dict[str, str]:
    if selection_id == "HTTPS_DEFAULT":
        return {"policy_id": selection_id, "auth_mode": "NONE"}
    return {"policy_id": selection_id, "auth_mode": "EXISTING"}


def _transport_model_eligible(component: str, model_hint: ModelHint | None) -> bool:
    if component != "vendor_panasonic":
        return True
    return model_hint is not None and model_hint.match_key == "wv-s2531l"


def _safe_selection_metadata(
    metadata: Mapping[str, object], sensitive_values: tuple[str, ...]
) -> dict[str, object]:
    """Keep credentials out of preflight diagnostics even when an ID reuses one."""
    return {
        key: value
        for key, value in metadata.items()
        if not isinstance(value, str)
        or not any(
            secret and secret.casefold() in value.casefold()
            for secret in sensitive_values
        )
    }
