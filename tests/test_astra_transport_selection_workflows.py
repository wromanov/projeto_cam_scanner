from __future__ import annotations

from pathlib import Path

import openpyxl

from cam_scanner.application.inventory_service import InventoryService
from cam_scanner.application.multi_workflow import MultiWorkflow
from cam_scanner.application.single_workflow import SingleWorkflow
from cam_scanner.config.models import EffectiveConfig, TransportProfile
from cam_scanner.domain.enums import CollectionStatus, MainMenuChoice
from cam_scanner.domain.models import CameraResult, CameraTarget, CollectionReport
from cam_scanner.snapshot.service import SnapshotFailure, SnapshotResult


class _Collector:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str, tuple[object, ...]]] = []

    def collect_report(self, target: CameraTarget, *, context) -> CollectionReport:
        plan = context.config.transport_plan
        self.calls.append((target.ip, target.username, target.password, plan.rules))
        result = CameraResult(
            ip=target.ip,
            status=CollectionStatus.SUCCESS,
            manufacturer="Panasonic" if target.username == "viewer-a" else "Axis",
            model="Synthetic model",
            serial=f"SERIAL-{target.username}",
        )
        return CollectionReport.from_camera_result(
            result,
            source="VENDOR",
            sensitive_values=(target.username, target.password),
        )


class _UI:
    def __init__(self, source: Path) -> None:
        self.source = source
        self.options = ()
        self.errors: list[str] = []
        self.completions: list[tuple[str, int, int]] = []

    def prompt_multi_input_path(self) -> str:
        return str(self.source)

    def prompt_multi_output_path(self, default_path: str) -> str:
        return default_path

    def prompt_transport_selection(self, options) -> str:
        self.options = options
        return "panasonic-field"

    def show_multi_error(self, message: str) -> None:
        self.errors.append(message)

    def show_multi_complete(self, path: str, camera_count: int, *, failed: int = 0) -> None:
        self.completions.append((path, camera_count, failed))


class _SnapshotService:
    def __init__(self) -> None:
        self.targets: list[str] = []

    def capture_one(self, target: CameraTarget, **_options) -> SnapshotResult:
        self.targets.append(target.ip)
        return SnapshotResult(failure=SnapshotFailure.UNSUPPORTED)


class _Progress:
    def start(self, _total: int) -> None:
        pass

    def advance(self, _ip: str, _status: str) -> None:
        pass

    def finish(self) -> None:
        pass


class _Writer:
    def write(self, path, _rows):
        return path


def test_single_transport_cancellation_precedes_collection_after_model_preflight() -> None:
    target = CameraTarget("192.0.2.10", "viewer-a", "secret-a")
    profile = TransportProfile(
        "panasonic-field", (target.ip,), "vendor_panasonic", "http", 8080,
        "NATIVE_DIGEST_EXISTING", "AUTH-2026-01", True,
    )
    collector = _Collector()
    service = InventoryService(
        collector, config=EffectiveConfig(transport_profiles=(profile,))
    )

    class UI:
        def prompt_camera_target(self):
            return target

        def prompt_manufacturer_hint(self):
            return "Panasonic"

        def prompt_transport_selection(self, options):
            assert next(item for item in options if item.selection_id == profile.id).http_rows == 1

        def prompt_model_hint(self):
            return "WV-S2531L"

        def show_transport_selection_cancelled(self):
            self.cancelled = True

        def post_query_menu(self):
            return MainMenuChoice.EXIT

    ui = UI()
    snapshots = _SnapshotService()

    result = SingleWorkflow(ui, service, snapshots).run()

    assert result is MainMenuChoice.EXIT
    assert ui.cancelled
    assert collector.calls == []
    assert snapshots.targets == []


def test_multi_freezes_profile_per_row_and_skips_ineligible_rows_before_io(
    tmp_path: Path,
) -> None:
    source = tmp_path / "input.xlsx"
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(("IP", "USERNAME", "PASSWORD", "FABRICANTE", "MODELO"))
    sheet.append(("192.0.2.10", "viewer-a", "secret-a", "Panasonic", "WV-S2531L"))
    sheet.append(("192.0.2.10", "viewer-b", "secret-b", "Axis", None))
    sheet.append(("192.0.2.11", "viewer-c", "secret-c", "Axis", None))
    workbook.save(source)
    workbook.close()

    profile = TransportProfile(
        "panasonic-field", ("192.0.2.10",), "vendor_panasonic", "http", 8080,
        "NATIVE_DIGEST_EXISTING", "AUTH-2026-01", True,
    )
    collector = _Collector()
    service = InventoryService(
        collector, config=EffectiveConfig(transport_profiles=(profile,))
    )
    ui = _UI(source)
    snapshots = _SnapshotService()
    workflow = MultiWorkflow(
        ui,
        service,
        snapshots,
        progress_reporter=_Progress(),
        excel_writer=_Writer(),
        max_workers=2,
    )

    workflow.run()

    option = next(item for item in ui.options if item.selection_id == profile.id)
    assert (option.http_rows, option.https_rows, option.ineligible_rows) == (1, 1, 1)
    assert len(collector.calls) == 2
    calls = {username: (ip, password, rules)
             for ip, username, password, rules in collector.calls}
    assert calls["viewer-a"] == (
        "192.0.2.10", "secret-a",
        (service.prepare_transport_for_row(
            "192.0.2.10", "Panasonic", profile.id, model_hint="WV-S2531L"
        )[0].transport_plan.rules[0],),
    )
    assert calls["viewer-c"] == ("192.0.2.11", "secret-c", ())
    assert [row.result.ip for row in workflow.completed_rows] == [
        "192.0.2.10", "192.0.2.10", "192.0.2.11",
    ]
    assert sorted(snapshots.targets) == ["192.0.2.10", "192.0.2.11"]
    assert not ui.errors
    assert ui.completions[0][1:] == (3, 1)
