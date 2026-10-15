"""Integrated one-camera workflow with canonical diagnostics and optional snapshot."""
from __future__ import annotations

import time

from cam_scanner.application.inventory_service import InventoryService
from cam_scanner.domain.enums import MainMenuChoice
from cam_scanner.domain.models import CameraTarget
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
        target_ip = target.ip
        started = time.monotonic()
        collect_execution = getattr(self._inventory_service, "collect_execution", None)
        context = None
        try:
            if callable(collect_execution):
                report, context = collect_execution(target)
            else:
                collect_report = getattr(self._inventory_service, "collect_report", None)
                report = collect_report(target) if callable(collect_report) else None
            result = (
                report.to_camera_result(target_ip)
                if report is not None
                else self._inventory_service.collect_one(target)
            )
            duration = max(0.0, float(time.monotonic() - started))
            snapshot: SnapshotResult | None = None
            if self._snapshot_service is not None:
                try:
                    if context is None:
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
