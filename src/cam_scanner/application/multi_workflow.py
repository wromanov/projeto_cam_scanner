"""Sequential MULTI workflow reusing the canonical inventory and snapshot services."""
from __future__ import annotations

from pathlib import Path

from cam_scanner.application.inventory_service import InventoryService
from cam_scanner.domain.enums import CollectionStatus, ErrorCode
from cam_scanner.domain.models import CameraResult, CameraTarget
from cam_scanner.excel.reader import ExcelInputError, ExcelInputRow, ExcelReader
from cam_scanner.excel.writer import ExcelOutputError, ExcelWriter, InventoryOutputRow
from cam_scanner.snapshot.service import SnapshotFailure, SnapshotResult, SnapshotService
from cam_scanner.terminal.progress import ProgressReporter
from cam_scanner.terminal.ui import TerminalUI

_INVALID_ROW_MESSAGE = "Linha inválida: informe IP, USERNAME e PASSWORD válidos."
_UNEXPECTED_ROW_MESSAGE = "Não foi possível processar esta linha da planilha."


class MultiWorkflow:
    """Read one credential row at a time, collect independently, and export safe results."""

    def __init__(
        self,
        ui: TerminalUI,
        inventory_service: InventoryService,
        snapshot_service: SnapshotService,
        excel_reader: ExcelReader | None = None,
        excel_writer: ExcelWriter | None = None,
        progress_reporter: ProgressReporter | None = None,
    ) -> None:
        self._ui = ui
        self._inventory_service = inventory_service
        self._snapshot_service = snapshot_service
        self._excel_reader = excel_reader or ExcelReader()
        self._excel_writer = excel_writer or ExcelWriter()
        self._progress = progress_reporter or ProgressReporter()

    def run(self) -> None:
        input_path = self._ui.prompt_multi_input_path()
        try:
            batch = self._excel_reader.read(input_path)
        except ExcelInputError as error:
            self._ui.show_multi_error(str(error))
            return

        default_output = _default_output_path(input_path)
        output_path = self._ui.prompt_multi_output_path(str(default_output))
        output_rows: list[InventoryOutputRow] = []
        self._progress.start(batch.total_rows)
        try:
            for input_row in batch.rows:
                output_row = self._process_row(input_row)
                output_rows.append(output_row)
                self._progress.advance(output_row.result.ip, output_row.result.status.value)
                del input_row
            output_file = self._excel_writer.write(output_path, output_rows)
            self._ui.show_multi_complete(output_file, len(output_rows))
        except ExcelInputError as error:
            self._ui.show_multi_error(str(error))
        except ExcelOutputError as error:
            self._ui.show_multi_error(str(error))
        except Exception:  # noqa: BLE001 - batch errors stay at the application boundary.
            self._ui.show_multi_error("O lote foi interrompido por uma falha local inesperada.")
        finally:
            self._progress.finish()

    def _process_row(self, row: ExcelInputRow) -> InventoryOutputRow:
        if not row.valid:
            return InventoryOutputRow(
                row.row_id,
                _invalid_row_result(row.ip),
            )

        target = CameraTarget(row.ip, row.username, row.password)
        try:
            result = self._inventory_service.collect_one(target)
        except Exception:  # noqa: BLE001 - a single camera cannot abort the batch.
            result = CameraResult(
                ip=row.ip,
                status=CollectionStatus.FAILED,
                error_code=ErrorCode.UNEXPECTED_ERROR,
                error_message=_UNEXPECTED_ROW_MESSAGE,
                duration=0.0,
            )

        snapshot: SnapshotResult | None = None
        if result.status is not CollectionStatus.FAILED:
            try:
                snapshot = self._snapshot_service.capture_one(
                    target,
                    manufacturer=result.manufacturer,
                    model=result.model,
                )
            except Exception:  # noqa: BLE001 - snapshot failure preserves collected identity.
                snapshot = SnapshotResult(failure=SnapshotFailure.UNEXPECTED)
        del target
        return InventoryOutputRow(row.row_id, result, snapshot)


def _invalid_row_result(ip: str) -> CameraResult:
    return CameraResult(
        ip=ip or "N/A",
        status=CollectionStatus.FAILED,
        error_code=ErrorCode.INVALID_INPUT,
        error_message=_INVALID_ROW_MESSAGE,
        duration=0.0,
    )


def _default_output_path(input_path: str | Path) -> Path:
    source = Path(input_path).expanduser()
    return source.with_name(f"{source.stem}_inventario.xlsx")
