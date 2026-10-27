from __future__ import annotations

from pathlib import Path

import pytest

openpyxl = pytest.importorskip("openpyxl")

from cam_scanner.domain.enums import CollectionStatus, ErrorCode
from cam_scanner.domain.models import CameraResult
from cam_scanner.excel.writer import ExcelOutputError, ExcelWriter, InventoryOutputRow, _cell


def test_writer_protects_formula_and_keeps_valid_xlsx_rows(tmp_path: Path) -> None:
    destination = tmp_path / "inventory.xlsx"
    result = CameraResult(
        ip="192.0.2.12",
        status=CollectionStatus.SUCCESS,
        model=" \t=1+1",
    )

    ExcelWriter().write(destination, [InventoryOutputRow(source_row=3, result=result)])

    workbook = openpyxl.load_workbook(destination, data_only=False)
    try:
        sheet = workbook["INVENTARIO"]
        assert sheet["F2"].value == "' \t=1+1"
        assert sheet["F2"].data_type != "f"
        assert sheet["A2"].value == 3
        assert "PASSWORD" not in " ".join(str(cell.value) for row in sheet.iter_rows() for cell in row)
    finally:
        workbook.close()
    assert list(tmp_path.glob("cam_scanner_*.xlsx.tmp")) == []


def test_writer_replaces_legacy_invalid_cell_instead_of_aborting() -> None:
    assert _cell("legacy\x01value") == "Dado inválido"


def test_writer_downgrades_invalid_identity_and_summarizes_exported_statuses(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "mixed.xlsx"
    invalid_identity = CameraResult(
        ip="192.0.2.13",
        status=CollectionStatus.SUCCESS,
        manufacturer="unknown",
        model="Model-A",
        serial="Serial-A",
    )
    valid_identity = CameraResult(
        ip="192.0.2.14",
        status=CollectionStatus.SUCCESS,
        manufacturer="Acme Cameras",
        model="Model-B",
        serial="Serial-B",
    )

    ExcelWriter().write(
        destination,
        [
            InventoryOutputRow(source_row=4, result=invalid_identity),
            InventoryOutputRow(source_row=5, result=valid_identity),
        ],
    )

    workbook = openpyxl.load_workbook(destination, data_only=True)
    try:
        inventory = workbook["INVENTARIO"]
        assert inventory["D2"].value == "Dado inválido"
        assert inventory["K2"].value == "PARTIAL_SUCCESS"
        assert inventory["D3"].value == "Acme Cameras"
        assert inventory["K3"].value == "SUCCESS"

        summary = dict(workbook["RESUMO"].iter_rows(min_row=2, values_only=True))
        assert summary["TOTAL"] == 2
        assert summary["SUCCESS"] == 1
        assert summary["PARTIAL_SUCCESS"] == 1
        assert summary["FAILED"] == 0
    finally:
        workbook.close()


def test_writer_localizes_invalid_nonessential_legacy_text(tmp_path: Path) -> None:
    destination = tmp_path / "legacy-cell.xlsx"
    result = CameraResult(
        ip="192.0.2.15",
        status=CollectionStatus.SUCCESS,
        manufacturer="Acme Cameras",
        model="Model-C",
        serial="Serial-C",
    )
    # Simulate an object persisted before the current CameraResult validation.
    object.__setattr__(result, "firmware", "old\x01firmware")

    ExcelWriter().write(destination, [InventoryOutputRow(source_row=6, result=result)])

    workbook = openpyxl.load_workbook(destination, data_only=True)
    try:
        inventory = workbook["INVENTARIO"]
        assert inventory["H2"].value == "Dado inválido"
        assert inventory["K2"].value == "SUCCESS"
    finally:
        workbook.close()


def test_writer_closes_workbook_when_summary_setup_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_workbook = openpyxl.Workbook
    instances = []

    class FailingSummaryWorkbook(original_workbook):
        def __init__(self):
            super().__init__()
            self.was_closed = False
            instances.append(self)

        def create_sheet(self, title=None, index=None):
            if title == "RESUMO":
                raise RuntimeError("private workbook diagnostic")
            return super().create_sheet(title=title, index=index)

        def close(self):
            self.was_closed = True
            return super().close()

    monkeypatch.setattr(openpyxl, "Workbook", FailingSummaryWorkbook)
    result = CameraResult(
        ip="192.0.2.16",
        status=CollectionStatus.FAILED,
        error_code=ErrorCode.ONVIF_ERROR,
        error_message="falha",
    )

    with pytest.raises(ExcelOutputError) as error:
        ExcelWriter().write(
            tmp_path / "summary-failure.xlsx",
            [InventoryOutputRow(source_row=7, result=result)],
        )

    assert "private workbook diagnostic" not in str(error.value)
    assert instances and instances[0].was_closed
    assert list(tmp_path.glob("cam_scanner_*.xlsx.tmp")) == []
