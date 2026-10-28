"""Integrated one-camera workflow with canonical diagnostics and optional snapshot."""
from __future__ import annotations

import inspect
import time

from cam_scanner.application.inventory_service import InventoryService, TransportInputDescriptor
from cam_scanner.domain.enums import MainMenuChoice
from cam_scanner.domain.models import (
    CameraTarget,
    CollectionAttempt,
    ModelHint,
    parse_model_hint,
)
from cam_scanner.snapshot.service import SnapshotFailure, SnapshotResult, SnapshotService
from cam_scanner.terminal.ui import TerminalUI


class SingleWorkflow:
    """Collect and render one camera, then return navigation to the controller."""

    def __init__(
        self,
        ui: TerminalUI,
        inventory_service: InventoryService,
        snapshot_service: SnapshotService | None = None,
    ) -> None:
        self._ui = ui
        self._inventory_service = inventory_service
        self._snapshot_service = snapshot_service

    def run(self) -> MainMenuChoice:
        target: CameraTarget = self._ui.prompt_camera_target()
        hint_prompt = getattr(self._ui, "prompt_manufacturer_hint", None)
        manufacturer_hint = hint_prompt() if callable(hint_prompt) else None
        model_prompt = getattr(self._ui, "prompt_model_hint", None)
        model_hint = None
        safe_model_hint = None
        model_prompted_early = False
        transport_selection_id = "HTTPS_DEFAULT"
        transport_config = None
        transport_selection_metadata = None
        transport_selection_blocked = False
        options_method = getattr(self._inventory_service, "transport_selection_options", None)
        selection_prompt = getattr(self._ui, "prompt_transport_selection", None)
        prepare_transport = getattr(self._inventory_service, "prepare_transport_for_row", None)
        if (
            callable(model_prompt)
            and callable(options_method)
            and callable(prepare_transport)
            and _panasonic_profile_may_apply(options_method, target.ip, manufacturer_hint)
        ):
            model_hint = model_prompt()
            model_prompted_early = True
            safe_model_hint = _safe_model_hint(
                model_hint, (target.username, target.password)
            )
            if getattr(self._ui, "has_pending_post_query_choice", False):
                return self._ui.post_query_menu()
        if callable(options_method) and callable(selection_prompt) and callable(prepare_transport):
            options = options_method((TransportInputDescriptor(
                0, target.ip, True, manufacturer_hint, safe_model_hint,
            ),))
            chosen = selection_prompt(options)
            if chosen is None:
                cancelled = getattr(self._ui, "show_transport_selection_cancelled", None)
                if callable(cancelled):
                    cancelled()
                return self._ui.post_query_menu()
            transport_selection_id = chosen
            (
                transport_config,
                transport_selection_blocked,
                transport_selection_metadata,
            ) = _prepare_transport(
                prepare_transport,
                target.ip,
                manufacturer_hint,
                transport_selection_id,
                safe_model_hint,
            )
        if callable(model_prompt) and not model_prompted_early:
            model_hint = model_prompt()
            safe_model_hint = _safe_model_hint(
                model_hint, (target.username, target.password)
            )
        target_ip = target.ip
        started = time.monotonic()
        collect_execution = getattr(self._inventory_service, "collect_execution", None)
        context = None
        try:
            if callable(collect_execution):
                try:
                    parameters = inspect.signature(collect_execution).parameters
                except (TypeError, ValueError):
                    parameters = {}
                accepts_kwargs = any(p.kind is inspect.Parameter.VAR_KEYWORD for p in parameters.values())
                options = {}
                if "manufacturer_hint" in parameters or accepts_kwargs:
                    options["manufacturer_hint"] = manufacturer_hint or None
                if "model_hint" in parameters or accepts_kwargs:
                    options["model_hint"] = model_hint
                if "transport_config" in parameters or accepts_kwargs:
                    options["transport_config"] = transport_config
                    options["transport_selection_id"] = transport_selection_id
                    options["transport_selection_metadata"] = transport_selection_metadata
                    options["transport_selection_blocked"] = transport_selection_blocked
                if options:
                    report, context = collect_execution(target, **options)
                else:
                    report, context = collect_execution(target)
            else:
                collect_report = getattr(self._inventory_service, "collect_report", None)
                report = collect_report(target) if callable(collect_report) else None
            result = (
                report.to_camera_result(target_ip)
                if report is not None
                else self._inventory_service.collect_one(target)
            )
            if report is not None and getattr(self._ui, "model_hint_invalid", False):
                report = report.with_attempt(CollectionAttempt(
                    stage="VALIDATE", operation="validate_model_hint", outcome="FAILED",
                    error_category="INVALID_INPUT",
                ))
            duration = max(0.0, float(time.monotonic() - started))
            snapshot: SnapshotResult | None = None
            if self._snapshot_service is not None:
                try:
                    if transport_selection_blocked:
                        snapshot = SnapshotResult(failure=SnapshotFailure.UNSUPPORTED)
                    elif _has_tls_failure(report) or (
                        context is not None and getattr(context, "tls_failed", False)
                    ):
                        snapshot = SnapshotResult(failure=SnapshotFailure.TLS_ERROR)
                    elif context is None:
                        snapshot = self._snapshot_service.capture_one(
                            target, manufacturer=result.manufacturer, model=result.model
                        )
                    else:
                        snapshot = self._snapshot_service.capture_one(
                            target,
                            manufacturer=result.manufacturer,
                            model=result.model,
                            context=context,
                        )
                except Exception:  # noqa: BLE001 - snapshot failure must not alter identity results.
                    snapshot = SnapshotResult(failure=SnapshotFailure.UNEXPECTED)
        finally:
            if context is not None:
                context.close()
        del target
        if report is not None:
            self._ui.render_report(
                report, ip=target_ip, duration=duration, snapshot=snapshot
            )
        else:
            self._ui.render_result(result, snapshot)
        return self._ui.post_query_menu()


def _has_tls_failure(report: object) -> bool:
    attempts = getattr(report, "attempts", ())
    return any(getattr(attempt, "error_category", None) == "TLS_ERROR" for attempt in attempts)


def _prepare_transport(
    prepare,
    ip: str,
    manufacturer_hint: str | None,
    selection_id: str,
    model_hint: ModelHint | None,
):
    try:
        parameters = inspect.signature(prepare).parameters
    except (TypeError, ValueError):
        parameters = {}
    accepts_kwargs = any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    )
    if "model_hint" in parameters or accepts_kwargs:
        return prepare(ip, manufacturer_hint, selection_id, model_hint=model_hint)
    return prepare(ip, manufacturer_hint, selection_id)


def _safe_model_hint(
    model_hint: ModelHint | str | None, sensitive_values: tuple[str, ...]
) -> ModelHint | None:
    value = model_hint.declared if isinstance(model_hint, ModelHint) else model_hint
    return parse_model_hint(value, sensitive_values=sensitive_values)


def _panasonic_profile_may_apply(options_method, ip: str, manufacturer_hint: str | None) -> bool:
    if not callable(options_method) or not isinstance(manufacturer_hint, str):
        return False
    normalized = manufacturer_hint.casefold().replace("/", " ").replace("-", " ")
    if "panasonic" not in normalized and "i pro" not in normalized:
        return False
    preliminary = options_method((TransportInputDescriptor(0, ip, True, manufacturer_hint),))
    return any(
        option.selection_id != "HTTPS_DEFAULT" and option.ineligible_rows > 0
        for option in preliminary
    )
