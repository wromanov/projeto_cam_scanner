"""Consolidated, password-free XLSX output boundary for MULTI."""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

from cam_scanner.domain.models import CameraResult

if TYPE_CHECKING:
    from cam_scanner.snapshot.service import SnapshotResult

_HEADERS = (
    "LINHA",
    "IP",
    "HOSTNAME",
    "FABRICANTE",
    "FABRICANTE_ORIGINAL",
    "MODELO",
    "NUMERO_SERIE",
    "FIRMWARE",
    "HARDWARE_ID",
    "MAC",
    "STATUS",
    "METODO_COLETA",
    "ERRO_CODIGO",
    "ERRO",
    "DURACAO_SEGUNDOS",
    "SNAPSHOT",
)


class ExcelOutputError(ValueError):
    """Sanitized workbook output error."""


@dataclass(frozen=True, slots=True)
class InventoryOutputRow:
    source_row: int
    result: CameraResult
    snapshot: SnapshotResult | None = None


class ExcelWriter:
    """Write ordered inventory and summary sheets without input credentials."""

    def write(self, path: str | Path, rows: list[InventoryOutputRow]) -> Path:
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font
        except ImportError:
            raise ExcelOutputError("O suporte XLSX não está disponível neste ambiente.") from None
        try:
            from openpyxl.drawing.image import Image as SpreadsheetImage
        except ImportError:
            SpreadsheetImage = None

        destination = Path(path).expanduser()
        if destination.exists():
            raise ExcelOutputError("O arquivo de saída já existe; escolha outro nome.")
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            raise ExcelOutputError("Não foi possível preparar a pasta de saída.") from None

        workbook = Workbook()
        inventory = workbook.active
        inventory.title = "INVENTARIO"
        inventory.append(_HEADERS)
        for cell in inventory[1]:
            cell.font = Font(bold=True)
        inventory.freeze_panes = "A2"
        inventory.auto_filter.ref = f"A1:P{max(1, len(rows) + 1)}"
        image_streams = []
        snapshot_count = 0

        for row_number, output_row in enumerate(rows, start=2):
            result = output_row.result
            snapshot = output_row.snapshot
            has_snapshot = snapshot is not None and snapshot.successful
            snapshot_label = "Incluído" if has_snapshot else "N/A"
            inventory.append(
                (
                    output_row.source_row,
                    _cell(result.ip),
                    _cell(result.hostname),
                    _cell(result.manufacturer),
                    _cell(result.manufacturer_original),
                    _cell(result.model),
                    _cell(result.serial),
                    _cell(result.firmware),
                    _cell(result.hardware_id),
                    _cell(result.mac),
                    result.status.value,
                    result.collection_method.value if result.collection_method else "N/A",
                    result.error_code.value if result.error_code else "N/A",
                    _cell(result.error_message),
                    result.duration,
                    snapshot_label,
                )
            )
            if has_snapshot:
                if SpreadsheetImage is None:
                    inventory.cell(row=row_number, column=16, value="Não incorporado")
                    continue
                try:
                    stream = BytesIO(snapshot.jpeg_bytes)
                    image = SpreadsheetImage(stream)
                    image.width = min(image.width, 320)
                    image.height = min(image.height, 180)
                    image.anchor = f"P{row_number}"
                    inventory.add_image(image)
                    inventory.row_dimensions[row_number].height = 105
                    image_streams.append(stream)
                    snapshot_count += 1
                except Exception:  # noqa: BLE001 - one bad image cannot abort the inventory export.
                    inventory.cell(row=row_number, column=16, value="Não incorporado")

        inventory.column_dimensions["A"].width = 10
        inventory.column_dimensions["B"].width = 18
        for column in "CDEFGHIJKLMNO":
            inventory.column_dimensions[column].width = 20
        inventory.column_dimensions["P"].width = 42

        summary = workbook.create_sheet("RESUMO")
        summary.append(("INDICADOR", "QUANTIDADE"))
        for cell in summary[1]:
            cell.font = Font(bold=True)
        counts = {
            "TOTAL": len(rows),
            "SUCCESS": sum(row.result.status.value == "SUCCESS" for row in rows),
            "PARTIAL_SUCCESS": sum(
                row.result.status.value == "PARTIAL_SUCCESS" for row in rows
            ),
            "FAILED": sum(row.result.status.value == "FAILED" for row in rows),
            "CANCELLED": sum(row.result.status.value == "CANCELLED" for row in rows),
            "SNAPSHOT_EMBEDDED": snapshot_count,
        }
        for label, count in counts.items():
            summary.append((label, count))
        summary.column_dimensions["A"].width = 26
        summary.column_dimensions["B"].width = 18
        summary.freeze_panes = "A2"

        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix="cam_scanner_",
                suffix=".xlsx.tmp",
                dir=destination.parent,
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
            workbook.save(temporary_path)
            try:
                os.link(temporary_path, destination)
            except FileExistsError:
                raise ExcelOutputError(
                    "O arquivo de saída já existe; escolha outro nome."
                ) from None
            temporary_path.unlink()
            temporary_path = None
            return destination
        except ExcelOutputError:
            raise
        except Exception:  # noqa: BLE001 - library/filesystem details are not user-facing.
            raise ExcelOutputError("Não foi possível gerar o arquivo XLSX de saída.") from None
        finally:
            workbook.close()
            for stream in image_streams:
                stream.close()
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass


def _cell(value: str | None) -> str:
    if value is None or not value.strip():
        return "N/A"
    if value.lstrip().startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value
