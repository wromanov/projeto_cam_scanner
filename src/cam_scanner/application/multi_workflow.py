"""Concurrent MULTI workflow reusing canonical services and ordered XLSX output."""
from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from pathlib import Path

from cam_scanner.application.inventory_service import InventoryService
from cam_scanner.config.models import DEFAULT_MAX_WORKERS, MAX_WORKERS, MIN_WORKERS
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
        max_workers: int = DEFAULT_MAX_WORKERS,
    ) -> None:
        if (
            isinstance(max_workers, bool)
            or not isinstance(max_workers, int)
            or not MIN_WORKERS <= max_workers <= MAX_WORKERS
        ):
            raise ValueError("max_workers deve ser um inteiro entre 1 e 32.")
        self._ui = ui
        self._inventory_service = inventory_service
        self._snapshot_service = snapshot_service
        self._excel_reader = excel_reader or ExcelReader()
        self._excel_writer = excel_writer or ExcelWriter()
        self._progress = progress_reporter or ProgressReporter()
        self._max_workers = max_workers

    def run(self) -> None:
        input_path = self._ui.prompt_multi_input_path()
        try:
            batch = self._excel_reader.read(input_path)
        except ExcelInputError as error:
            self._ui.show_multi_error(str(error))
            return

        default_output = _default_output_path(input_path)
        output_path = self._ui.prompt_multi_output_path(str(default_output))
        output_rows: list[InventoryOutputRow | None] = [None] * batch.total_rows
        self._progress.start(batch.total_rows)
        executor = ThreadPoolExecutor(max_workers=self._max_workers)
        pending: dict[Future[InventoryOutputRow], tuple[int, int, str]] = {}
        rows = iter(batch.rows)
        position = 0
        exhausted = False
        try:
            while pending or not exhausted:
                # Keep at most 2x workers submitted; 2,300 rows never create 2,300 futures.
                while len(pending) < self._max_workers * 2 and not exhausted:
                    try:
                        input_row = next(rows)
                    except StopIteration:
                        exhausted = True
                        break
                    current_position = position
                    position += 1
                    if not input_row.valid:
                        output_row = self._process_row(input_row)
                        output_rows[current_position] = output_row
                        self._progress.advance(output_row.result.ip, output_row.result.status.value)
                        continue
                    pending[executor.submit(self._process_row, input_row)] = (
                        current_position,
                        input_row.row_id,
                        input_row.ip,
                    )

                if pending:
                    completed, _ = wait(pending, return_when=FIRST_COMPLETED)
                    for future in completed:
                        current_position, row_id, ip = pending.pop(future)
                        try:
                            output_row = future.result()
                        except Exception:  # noqa: BLE001 - isolate unexpected Future failures.
                            output_row = InventoryOutputRow(
                                row_id,
                                _unexpected_row_result(ip),
                            )
                        output_rows[current_position] = output_row
                        self._progress.advance(output_row.result.ip, output_row.result.status.value)

            executor.shutdown(wait=True)
            if position != batch.total_rows or any(row is None for row in output_rows):
                raise ExcelInputError("A quantidade de linhas da planilha mudou durante a leitura.")
            ordered_rows = [row for row in output_rows if row is not None]
            output_file = self._excel_writer.write(output_path, ordered_rows)
            failed = sum(
                row is not None and row.result.status is CollectionStatus.FAILED
                for row in output_rows
            )
            self._ui.show_multi_complete(output_file, len(output_rows), failed=failed)
        except KeyboardInterrupt:
            executor.shutdown(wait=True, cancel_futures=True)
            raise
        except ExcelInputError as error:
            executor.shutdown(wait=True, cancel_futures=True)
            self._ui.show_multi_error(str(error))
        except ExcelOutputError as error:
            executor.shutdown(wait=True, cancel_futures=True)
            self._ui.show_multi_error(str(error))
        except Exception:  # noqa: BLE001 - batch errors stay at the application boundary.
            executor.shutdown(wait=True, cancel_futures=True)
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


def _unexpected_row_result(ip: str) -> CameraResult:
    return CameraResult(
        ip=ip,
        status=CollectionStatus.FAILED,
        error_code=ErrorCode.UNEXPECTED_ERROR,
        error_message=_UNEXPECTED_ROW_MESSAGE,
        duration=0.0,
    )


def _default_output_path(input_path: str | Path) -> Path:
    source = Path(input_path).expanduser()
    return source.with_name(f"{source.stem}_inventario.xlsx")
