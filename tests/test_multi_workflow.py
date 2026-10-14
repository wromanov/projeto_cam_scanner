from __future__ import annotations

import io
import threading
import zipfile
from pathlib import Path

import pytest

openpyxl = pytest.importorskip("openpyxl")
Image = pytest.importorskip("PIL.Image")

from cam_scanner.application.controller import ApplicationController
from cam_scanner.application.inventory_service import InventoryService
from cam_scanner.application.multi_workflow import MultiWorkflow
from cam_scanner.domain.enums import CollectionStatus, MainMenuChoice
from cam_scanner.domain.models import CameraResult, CameraTarget
from cam_scanner.excel.reader import ExcelReader
from cam_scanner.excel.writer import ExcelWriter
from cam_scanner.snapshot.service import (
    SnapshotCaptureError,
    SnapshotFailure,
    SnapshotService,
)
from cam_scanner.terminal.ui import TerminalUI


def _jpeg_fixture() -> bytes:
    source = Image.new("RGB", (640, 320), color=(50, 100, 150))
    output = io.BytesIO()
    source.save(output, format="JPEG", quality=90)
    return output.getvalue()


class FakeCollector:
    def __init__(self) -> None:
        self.credentials: list[tuple[str, str, str]] = []

    def collect(self, target: CameraTarget) -> CameraResult:
        self.credentials.append((target.ip, target.username, target.password))
        return CameraResult(
            ip=target.ip,
            status=CollectionStatus.SUCCESS,
            manufacturer="Hikvision",
            model="DS-KD8003",
            serial=f"SERIAL-{target.ip.rsplit('.', maxsplit=1)[-1]}",
            firmware="1.0",
            duration=0.125,
        )


class SuccessfulSnapshotProvider:
    def __init__(self, image_bytes: bytes) -> None:
        self.image_bytes = image_bytes

    def capture(self, _target: CameraTarget, **_context: object) -> bytes:
        return self.image_bytes


class FailingProvider:
    def capture(self, _target: CameraTarget, **_context: object) -> bytes:
        raise RuntimeError("offline fixture has no camera transport")


class NoopWorkflow:
    def run(self) -> MainMenuChoice:
        return MainMenuChoice.EXIT


class RecordingProgress:
    def __init__(self) -> None:
        self.total = None
        self.steps: list[tuple[str, str]] = []
        self.finished = False

    def start(self, total: int) -> None:
        self.total = total

    def advance(self, ip: str, status: str) -> None:
        self.steps.append((ip, status))

    def finish(self) -> None:
        self.finished = True


def _input_workbook(path: Path) -> None:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(("Password", "extra", "Ip", "Username"))
    sheet.append(("pw-one", "ignored", "192.0.2.10", "user-one"))
    sheet.append((None, None, None, None))
    sheet.append(("pw-missing-user", "ignored", "192.0.2.11", None))
    sheet.append(("pw-two", "ignored", "192.0.2.12", "user-two"))
    workbook.save(path)
    workbook.close()


def test_excel_reader_accepts_reordered_case_insensitive_headers_and_hides_credentials(
    tmp_path: Path,
) -> None:
    source = tmp_path / "input.xlsx"
    _input_workbook(source)

    batch = ExcelReader().read(source)
    rows = list(batch.rows)

    assert batch.total_rows == 3
    assert [row.row_id for row in rows] == [2, 4, 5]
    assert rows[0].valid
    assert rows[0].ip == "192.0.2.10"
    assert rows[0].username == "user-one"
    assert rows[0].password == "pw-one"
    assert not rows[1].valid
    assert rows[1].username == rows[1].password == ""
    assert "pw-one" not in repr(rows[0])
    assert "user-one" not in repr(rows[0])


def test_multi_workflow_runs_end_to_end_offline_and_exports_no_passwords(
    tmp_path: Path,
) -> None:
    source = tmp_path / "cameras.xlsx"
    destination = tmp_path / "inventory.xlsx"
    _input_workbook(source)
    collector = FakeCollector()
    inventory_service = InventoryService(collector)
    image_bytes = _jpeg_fixture()
    snapshot_service = SnapshotService(
        SuccessfulSnapshotProvider(image_bytes),
        FailingProvider(),
        FailingProvider(),
    )
    progress = RecordingProgress()
    output: list[str] = []
    responses = iter(("2", str(source), str(destination), "3"))
    ui = TerminalUI(
        input_fn=lambda _prompt: next(responses),
        password_fn=lambda _prompt: pytest.fail("MULTI must read passwords only from XLSX"),
        output_fn=output.append,
    )
    multi = MultiWorkflow(
        ui,
        inventory_service,
        snapshot_service,
        excel_reader=ExcelReader(),
        excel_writer=ExcelWriter(),
        progress_reporter=progress,
        max_workers=1,
    )
    controller = ApplicationController(ui, NoopWorkflow(), multi)

    controller.run()

    assert collector.credentials == [
        ("192.0.2.10", "user-one", "pw-one"),
        ("192.0.2.12", "user-two", "pw-two"),
    ]
    assert progress.total == 3
    assert len(progress.steps) == 3
    assert ("192.0.2.11", "FAILED") in progress.steps
    assert progress.finished
    assert destination.is_file()

    exported = openpyxl.load_workbook(destination, data_only=True)
    inventory = exported["INVENTARIO"]
    assert inventory.freeze_panes == "A2"
    assert inventory.auto_filter.ref == "A1:P4"
    headers = [cell.value for cell in inventory[1]]
    assert "PASSWORD" not in headers
    assert [inventory.cell(row, 1).value for row in range(2, 5)] == [2, 4, 5]
    assert [inventory.cell(row, 11).value for row in range(2, 5)] == [
        "SUCCESS",
        "FAILED",
        "SUCCESS",
    ]
    assert len(inventory._images) == 2
    summary = exported["RESUMO"]
    assert summary["A2"].value == "TOTAL"
    assert summary["B2"].value == 3
    assert summary["A3"].value == "SUCCESS"
    assert summary["B3"].value == 2
    assert summary["A5"].value == "FAILED"
    assert summary["B5"].value == 1
    exported.close()

    with zipfile.ZipFile(destination) as archive:
        content = b"".join(archive.read(name) for name in archive.namelist())
    assert b"pw-one" not in content
    assert b"pw-two" not in content
    assert b"pw-missing-user" not in content
    assert "MULTI concluído" in "\n".join(output)


def test_excel_writer_refuses_to_overwrite_existing_output(tmp_path: Path) -> None:
    destination = tmp_path / "existing.xlsx"
    destination.write_bytes(b"preserve")

    from cam_scanner.excel.writer import ExcelOutputError

    with pytest.raises(ExcelOutputError):
        ExcelWriter().write(destination, [])

    assert destination.read_bytes() == b"preserve"


def test_multi_parallel_offline_smoke_orders_rows_and_keeps_passwords_private(
    tmp_path: Path,
) -> None:
    source = tmp_path / "cameras-p5.xlsx"
    destination = tmp_path / "inventory-p5.xlsx"
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(("IP", "USERNAME", "PASSWORD"))
    passwords: list[str] = []
    for index in range(9):
        password = f"P5_PASSWORD_CANARY_{index}"
        passwords.append(password)
        sheet.append(
            (f"192.0.2.{101 + index}", f"P5_USER_{index}", password)
        )
    sheet.append(("192.0.2.250", None, "P5_INVALID_PASSWORD_CANARY"))
    workbook.save(source)
    workbook.close()

    first_started = threading.Event()
    release_first = threading.Event()
    credential_lock = threading.Lock()
    credentials: list[tuple[str, str, str]] = []

    class Collector:
        def collect(self, target: CameraTarget) -> CameraResult:
            with credential_lock:
                credentials.append((target.ip, target.username, target.password))
            if target.ip == "192.0.2.101":
                first_started.set()
                assert release_first.wait(timeout=5)
            elif target.ip == "192.0.2.102":
                assert first_started.wait(timeout=5)
                release_first.set()
            if target.ip == "192.0.2.103":
                return CameraResult(ip=target.ip, status=CollectionStatus.FAILED)
            return CameraResult(
                ip=target.ip,
                status=CollectionStatus.SUCCESS,
                manufacturer="Hikvision",
                model="DS-KD8003",
                serial=f"SERIAL-{target.ip.rsplit('.', maxsplit=1)[-1]}",
            )

    image_bytes = _jpeg_fixture()

    class SnapshotProvider:
        def capture(self, target: CameraTarget, **_context: object) -> bytes:
            if target.ip in {"192.0.2.101", "192.0.2.105"}:
                return image_bytes
            raise SnapshotCaptureError(SnapshotFailure.UNSUPPORTED)

    snapshot_service = SnapshotService(
        SnapshotProvider(), SnapshotProvider(), SnapshotProvider()
    )
    output: list[str] = []
    responses = iter((str(source), str(destination)))
    ui = TerminalUI(
        input_fn=lambda _prompt: next(responses),
        output_fn=output.append,
    )
    progress = RecordingProgress()
    workflow = MultiWorkflow(
        ui,
        InventoryService(Collector()),
        snapshot_service,
        excel_reader=ExcelReader(),
        excel_writer=ExcelWriter(),
        progress_reporter=progress,
        max_workers=8,
    )
    workflow.run()

    assert destination.is_file()
    assert len(credentials) == 9
    assert len({(ip, username, password) for ip, username, password in credentials}) == 9
    assert all(password not in "\n".join(output) for password in passwords)
    assert progress.total == 10
    assert len(progress.steps) == 10
    assert progress.finished
    assert any("10 linhas processadas" in item and "2 falhas" in item for item in output)

    exported = openpyxl.load_workbook(destination, data_only=True)
    inventory = exported["INVENTARIO"]
    assert [inventory.cell(row, 1).value for row in range(2, 12)] == list(range(2, 12))
    assert [inventory.cell(row, 11).value for row in range(2, 12)] == [
        "SUCCESS", "SUCCESS", "FAILED", "SUCCESS", "SUCCESS",
        "SUCCESS", "SUCCESS", "SUCCESS", "SUCCESS", "FAILED",
    ]
    assert [image.anchor._from.row for image in inventory._images] == [1, 5]
    assert "PASSWORD" not in [cell.value for cell in inventory[1]]
    summary = exported["RESUMO"]
    assert summary["B2"].value == 10
    assert summary["B5"].value == 2
    assert summary["B7"].value == 2
    exported.close()

    with zipfile.ZipFile(destination) as archive:
        content = b"".join(archive.read(name) for name in archive.namelist())
    assert all(password.encode() not in content for password in passwords)
    assert b"P5_INVALID_PASSWORD_CANARY" not in content
