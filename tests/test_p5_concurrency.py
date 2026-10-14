from __future__ import annotations

import threading
from pathlib import Path

import pytest

from cam_scanner.application.multi_workflow import MultiWorkflow
from cam_scanner.config.loader import load_settings
from cam_scanner.config.models import EffectiveConfig
from cam_scanner.domain.enums import CollectionStatus
from cam_scanner.domain.models import CameraResult, CameraTarget
from cam_scanner.excel.reader import ExcelInputBatch, ExcelInputRow
from cam_scanner.excel.writer import InventoryOutputRow
from cam_scanner.snapshot.service import SnapshotResult


class FakeUI:
    def __init__(self, destination: str = "unused.xlsx") -> None:
        self.destination = destination
        self.completed: tuple[str, int, int] | None = None
        self.errors: list[str] = []

    def prompt_multi_input_path(self) -> str:
        return "input.xlsx"

    def prompt_multi_output_path(self, _default: str) -> str:
        return self.destination

    def show_multi_complete(self, path: str, count: int, *, failed: int = 0) -> None:
        self.completed = (str(path), count, failed)

    def show_multi_error(self, message: str) -> None:
        self.errors.append(message)


class FakeReader:
    def __init__(self, rows: list[ExcelInputRow]) -> None:
        self.rows = rows

    def read(self, _path: str) -> ExcelInputBatch:
        return ExcelInputBatch(len(self.rows), iter(self.rows))


class FakeWriter:
    def __init__(self) -> None:
        self.rows: list[InventoryOutputRow] = []

    def write(self, path: str, rows: list[InventoryOutputRow]) -> Path:
        self.rows = rows
        return Path(path)


class FakeSnapshots:
    def capture_one(self, _target: CameraTarget, **_context: object) -> SnapshotResult:
        return SnapshotResult()


class RecordingProgress:
    def __init__(self) -> None:
        self.total = 0
        self.results: list[tuple[str, str]] = []
        self.finished = False

    def start(self, total: int) -> None:
        self.total = total

    def advance(self, ip: str, status: str) -> None:
        self.results.append((ip, status))

    def finish(self) -> None:
        self.finished = True


def _rows(count: int) -> list[ExcelInputRow]:
    return [
        ExcelInputRow(i + 2, f"192.0.2.{i + 1}", f"user-{i}", f"password-{i}")
        for i in range(count)
    ]


def _workflow(rows, collector, *, max_workers: int, writer=None, progress=None):
    ui = FakeUI()
    writer = writer or FakeWriter()
    progress = progress or RecordingProgress()
    workflow = MultiWorkflow(
        ui,
        collector,
        FakeSnapshots(),
        excel_reader=FakeReader(rows),
        excel_writer=writer,
        progress_reporter=progress,
        max_workers=max_workers,
    )
    return workflow, ui, writer, progress


def test_max_workers_one_is_sequential_and_credentials_are_per_target() -> None:
    active = 0
    maximum = 0
    guard = threading.Lock()
    observed: list[tuple[str, str, str, CameraTarget]] = []

    class Collector:
        def collect_one(self, target: CameraTarget) -> CameraResult:
            nonlocal active, maximum
            with guard:
                active += 1
                maximum = max(maximum, active)
                observed.append((target.ip, target.username, target.password, target))
                active -= 1
            return CameraResult(ip=target.ip, status=CollectionStatus.SUCCESS)

    workflow, _ui, _writer, progress = _workflow(_rows(4), Collector(), max_workers=1)
    workflow.run()

    assert maximum == 1
    assert len({id(target) for *_creds, target in observed}) == 4
    assert {(ip, username, password) for ip, username, password, _ in observed} == {
        (f"192.0.2.{i + 1}", f"user-{i}", f"password-{i}") for i in range(4)
    }
    assert len(progress.results) == 4


@pytest.mark.parametrize("worker_count", [8, 32])
def test_configured_worker_counts_allow_real_overlap(worker_count: int) -> None:
    barrier = threading.Barrier(worker_count)
    guard = threading.Lock()
    active = 0
    maximum = 0

    class Collector:
        def collect_one(self, target: CameraTarget) -> CameraResult:
            nonlocal active, maximum
            with guard:
                active += 1
                maximum = max(maximum, active)
            barrier.wait(timeout=5)
            with guard:
                active -= 1
            return CameraResult(ip=target.ip, status=CollectionStatus.SUCCESS)

    workflow, ui, _writer, _progress = _workflow(
        _rows(worker_count), Collector(), max_workers=worker_count
    )
    workflow.run()

    assert maximum == worker_count
    assert ui.completed == ("unused.xlsx", worker_count, 0)


@pytest.mark.parametrize("workers", [0, 33, -1, True, 1.5])
def test_worker_values_outside_integer_range_are_rejected(workers) -> None:
    with pytest.raises(ValueError, match="1 e 32"):
        EffectiveConfig(max_workers=workers)
    with pytest.raises(ValueError, match="1 e 32"):
        _workflow([], object(), max_workers=workers)


def test_configured_default_worker_value_is_loaded_and_validated(tmp_path: Path) -> None:
    settings = tmp_path / "settings.toml"
    settings.write_text("[concurrency]\ndefault_max_workers = 6\n", encoding="utf-8")
    assert load_settings(settings).max_workers == 6
    settings.write_text("[concurrency]\ndefault_max_workers = 33\n", encoding="utf-8")
    from cam_scanner.domain.errors import ConfigurationError

    with pytest.raises(ConfigurationError):
        load_settings(settings)


def test_out_of_order_completions_keep_input_order_and_isolate_failures() -> None:
    first_started = threading.Event()
    release_first = threading.Event()
    second_done = threading.Event()

    class Collector:
        def collect_one(self, target: CameraTarget) -> CameraResult:
            if target.ip.endswith(".1"):
                first_started.set()
                assert release_first.wait(timeout=5)
            else:
                assert first_started.wait(timeout=5)
                second_done.set()
                release_first.set()
            if target.ip.endswith(".3"):
                raise RuntimeError("do not expose this diagnostic")
            return CameraResult(ip=target.ip, status=CollectionStatus.SUCCESS)

    writer = FakeWriter()
    progress = RecordingProgress()
    workflow, ui, _writer, _progress = _workflow(
        _rows(3), Collector(), max_workers=3, writer=writer, progress=progress
    )
    workflow.run()

    assert second_done.is_set()
    assert [row.source_row for row in writer.rows] == [2, 3, 4]
    assert [row.result.status for row in writer.rows] == [
        CollectionStatus.SUCCESS,
        CollectionStatus.SUCCESS,
        CollectionStatus.FAILED,
    ]
    assert progress.total == 3
    assert len(progress.results) == 3
    assert ui.completed == ("unused.xlsx", 3, 1)
    assert not ui.errors


def test_future_exception_becomes_sanitized_row_and_ctrl_c_skips_export() -> None:
    rows = _rows(1)
    workflow, ui, writer, progress = _workflow(rows, object(), max_workers=1)

    def unexpected(_row):
        raise RuntimeError("password-secret-canary")

    workflow._process_row = unexpected
    workflow.run()

    assert writer.rows[0].result.status is CollectionStatus.FAILED
    assert writer.rows[0].result.error_message == "Não foi possível processar esta linha da planilha."
    assert "password-secret-canary" not in repr(writer.rows)
    assert ui.completed == ("unused.xlsx", 1, 1)
    assert len(progress.results) == 1

    class InterruptingProgress(RecordingProgress):
        def advance(self, _ip: str, _status: str) -> None:
            raise KeyboardInterrupt

    interrupted, interrupted_ui, interrupted_writer, interrupted_progress = _workflow(
        rows, object(), max_workers=1, progress=InterruptingProgress()
    )
    with pytest.raises(KeyboardInterrupt):
        interrupted.run()
    assert interrupted_writer.rows == []
    assert interrupted_ui.completed is None
    assert interrupted_progress.finished


def test_incomplete_input_iteration_does_not_export_partial_batch() -> None:
    workflow, ui, writer, _progress = _workflow(
        _rows(1),
        object(),
        max_workers=1,
    )
    workflow._excel_reader = type(
        "TruncatedReader",
        (),
        {"read": lambda _self, _path: ExcelInputBatch(2, iter(_rows(1)))},
    )()
    workflow._process_row = lambda row: InventoryOutputRow(
        row.row_id,
        CameraResult(ip=row.ip, status=CollectionStatus.SUCCESS),
    )

    workflow.run()

    assert writer.rows == []
    assert ui.completed is None
    assert ui.errors == ["A quantidade de linhas da planilha mudou durante a leitura."]
