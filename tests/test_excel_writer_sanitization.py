from __future__ import annotations

from pathlib import Path

import pytest

openpyxl = pytest.importorskip("openpyxl")

from cam_scanner.domain.enums import CollectionStatus
from cam_scanner.domain.models import CameraResult
from cam_scanner.excel.writer import ExcelWriter, InventoryOutputRow, _cell


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
