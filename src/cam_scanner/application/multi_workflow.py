"""Concurrent MULTI workflow reusing canonical services and ordered XLSX output."""
from __future__ import annotations

import inspect
import threading
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from pathlib import Path

from cam_scanner.application.collection_context import CollectionContext
from cam_scanner.application.inventory_service import (
    InventoryService,
    TransportInputDescriptor,
)
from cam_scanner.config.models import DEFAULT_MAX_WORKERS, MAX_WORKERS, MIN_WORKERS
from cam_scanner.domain.enums import CollectionStatus, ErrorCode
from cam_scanner.domain.errors import ConfigurationError
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
        self._completed_rows: tuple[InventoryOutputRow, ...] = ()

    @property
    def completed_rows(self) -> tuple[InventoryOutputRow, ...]:
        """Rows completed before a run ended, including safe partial results on cancel."""
        return self._completed_rows

    def run(self) -> None:
        input_path = self._ui.prompt_multi_input_path()
        try:
            batch = self._excel_reader.read(input_path)
        except ExcelInputError as error:
            self._ui.show_multi_error(str(error))
            return

        default_output = _default_output_path(input_path)
        output_path = self._ui.prompt_multi_output_path(str(default_output))
        try:
            preflight_rows = tuple(
                TransportInputDescriptor(
                    row.row_id, row.ip, row.valid, row.manufacturer_hint,
                    row.model_hint,
                )
                for row in batch.rows
            )
        except ExcelInputError as error:
            self._ui.show_multi_error(str(error))
            return
        if len(preflight_rows) != batch.total_rows:
            self._ui.show_multi_error("A quantidade de linhas mudou durante o pré-voo.")
            return
        selection_id = "HTTPS_DEFAULT"
        prepared_transport: dict[
            int, tuple[object, bool, dict[str, str | None]]
        ] = {}
        options_method = getattr(self._inventory_service, "transport_selection_options", None)
        prepare_method = getattr(self._inventory_service, "prepare_transport_for_row", None)
        selection_prompt = getattr(self._ui, "prompt_transport_selection", None)
        if callable(options_method) and callable(prepare_method) and callable(selection_prompt):
            try:
                selected = selection_prompt(options_method(preflight_rows))
                if selected is None:
                    cancelled = getattr(self._ui, "show_transport_selection_cancelled", None)
                    if callable(cancelled):
                        cancelled()
                    return
                selection_id = selected
                for row in preflight_rows:
                    if not row.valid:
                        continue
                    prepared_transport[row.row_id] = prepare_method(
                        row.ip,
                        row.manufacturer_hint,
                        selection_id,
                        **_supported_kwargs(prepare_method, model_hint=row.model_hint),
                    )
            except (ExcelInputError, ConfigurationError) as error:
                self._ui.show_multi_error(str(error))
                return
        try:
            batch = self._excel_reader.read(input_path)
            if batch.total_rows != len(preflight_rows):
                raise ExcelInputError(
                    "A quantidade de linhas mudou após o pré-voo de transporte."
                )
        except ExcelInputError as error:
            self._ui.show_multi_error(str(error))
            return
        output_rows: list[InventoryOutputRow | None] = [None] * batch.total_rows
        self._completed_rows = ()
        self._progress.start(batch.total_rows)
        executor = ThreadPoolExecutor(max_workers=self._max_workers)
        pending: dict[
            Future[InventoryOutputRow],
            tuple[int, int, str, CollectionContext | None],
        ] = {}
        cancel_event = threading.Event()
        rows = iter(batch.rows)
        position = 0
        exhausted = False
        try:
            while pending or not exhausted:
                # Keep at most 2x workers submitted; 2,300 rows never create 2,300 futures.
                while (
                    len(pending) < self._max_workers * 2
                    and not exhausted
                    and not cancel_event.is_set()
                ):
                    try:
                        input_row = next(rows)
                    except StopIteration:
                        exhausted = True
                        break
                    current_position = position
                    position += 1
                    if not input_row.valid:
                        output_row = self._process_row(input_row, cancel_event=cancel_event)
                        output_rows[current_position] = output_row
                        self._remember_completed(output_rows)
                        self._progress.advance(output_row.result.ip, output_row.result.status.value)
                        continue
                    expected = preflight_rows[current_position]
                    current_spec = TransportInputDescriptor(
                        input_row.row_id, input_row.ip, input_row.valid,
                        input_row.manufacturer_hint, input_row.model_hint,
                    )
                    if current_spec != expected:
                        raise ExcelInputError(
                            "A planilha mudou após o pré-voo de transporte."
                        )
                    context = self._create_context(
                        input_row,
                        cancel_event,
                        prepared_transport.get(input_row.row_id),
                        selection_id,
                    )
                    try:
                        future = executor.submit(
                            self._process_row,
                            input_row,
                            cancel_event=cancel_event,
                            execution_context=context,
                        )
                    except BaseException:
                        if context is not None:
                            context.close()
                        raise
                    pending[future] = (
                        current_position, input_row.row_id, input_row.ip, context
                    )

                if cancel_event.is_set():
                    raise ExcelInputError("O lote foi cancelado antes da exportação.")

                if pending:
                    completed, _ = wait(pending, return_when=FIRST_COMPLETED)
                    for future in completed:
                        current_position, row_id, ip, _context = pending[future]
                        try:
                            output_row = future.result()
                        except Exception:  # noqa: BLE001 - isolate unexpected Future failures.
                            output_row = InventoryOutputRow(
                                row_id,
                                _unexpected_row_result(ip),
                            )
                        output_rows[current_position] = output_row
                        pending.pop(future)
                        self._remember_completed(output_rows)
                        self._progress.advance(output_row.result.ip, output_row.result.status.value)

            executor.shutdown(wait=True)
            if cancel_event.is_set():
                raise ExcelInputError("O lote foi cancelado antes da exportação.")
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
            self._cancel_and_collect(executor, pending, output_rows, cancel_event)
            raise
        except ExcelInputError as error:
            self._cancel_and_collect(executor, pending, output_rows, cancel_event)
            self._ui.show_multi_error(str(error))
        except ExcelOutputError as error:
            self._cancel_and_collect(executor, pending, output_rows, cancel_event)
            self._ui.show_multi_error(str(error))
        except Exception:  # noqa: BLE001 - batch errors stay at the application boundary.
            self._cancel_and_collect(executor, pending, output_rows, cancel_event)
            self._ui.show_multi_error("O lote foi interrompido por uma falha local inesperada.")
        finally:
            self._progress.finish()

    def _process_row(
        self,
        row: ExcelInputRow,
        *,
        cancel_event: threading.Event | None = None,
        execution_context: CollectionContext | None = None,
    ) -> InventoryOutputRow:
        if not row.valid:
            return InventoryOutputRow(
                row.row_id,
                _invalid_row_result(row.ip),
            )

        target = CameraTarget(row.ip, row.username, row.password)
        context = execution_context
        report = None
        try:
            try:
                collect_execution = getattr(self._inventory_service, "collect_execution", None)
                if callable(collect_execution):
                    if context is None:
                        report, context = collect_execution(
                            target,
                            cancel_event=cancel_event,
                            manufacturer_hint=row.manufacturer_hint,
                            **_supported_kwargs(collect_execution, model_hint=row.model_hint),
                        )
                    else:
                        report, context = collect_execution(target, context=context)
                    if context is not None and row.model_hint_invalid:
                        _set_context_attribute(context, "model_hint_invalid", True)
                    if report is not None and row.model_hint is not None:
                        report = report.with_model_hint(row.model_hint)
                    if report is not None and row.model_hint_invalid:
                        from cam_scanner.domain.models import CollectionAttempt

                        if not any(
                            item.operation == "validate_model_hint" for item in report.attempts
                        ):
                            report = report.with_attempt(CollectionAttempt(
                                stage="VALIDATE", operation="validate_model_hint", outcome="FAILED",
                                error_category="INVALID_INPUT",
                            ))
                    result = report.to_camera_result(target.ip)
                else:
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
            try:
                if context is not None and getattr(context, "transport_selection_blocked", False):
                    snapshot = SnapshotResult(failure=SnapshotFailure.UNSUPPORTED)
                elif _has_tls_failure(report) or (
                    context is not None and getattr(context, "tls_failed", False)
                ):
                    snapshot = SnapshotResult(failure=SnapshotFailure.TLS_ERROR)
                elif context is None:
                    snapshot = self._snapshot_service.capture_one(
                        target,
                        manufacturer=result.manufacturer,
                        model=result.model,
                    )
                else:
                    snapshot = self._snapshot_service.capture_one(
                        target,
                        manufacturer=result.manufacturer,
                        model=result.model,
                        context=context,
                    )
            except Exception:  # noqa: BLE001 - snapshot failure preserves collected identity.
                snapshot = SnapshotResult(failure=SnapshotFailure.UNEXPECTED)
            return InventoryOutputRow(row.row_id, result, snapshot, report)
        finally:
            if context is not None:
                context.close()
            del target

    def _create_context(
        self,
        row: ExcelInputRow,
        cancel_event: threading.Event,
        prepared_transport: tuple[object, bool, dict[str, str | None]] | None = None,
        selection_id: str = "HTTPS_DEFAULT",
    ) -> CollectionContext | None:
        """Start the per-camera deadline before the executor queue can delay its worker."""
        if not row.valid:
            return None
        create_context = getattr(self._inventory_service, "create_context", None)
        collect_execution = getattr(self._inventory_service, "collect_execution", None)
        if not callable(create_context) or not callable(collect_execution):
            return None
        target = CameraTarget(row.ip, row.username, row.password)
        context_options: dict[str, object] = {
            "cancel_event": cancel_event,
            "manufacturer_hint": row.manufacturer_hint,
            "model_hint": row.model_hint,
        }
        if prepared_transport is not None:
            config, blocked, metadata = prepared_transport
            context_options.update({
                "transport_config": config,
                "transport_selection_id": selection_id,
                "transport_selection_metadata": metadata,
                "transport_selection_blocked": blocked,
            })
        context = create_context(
            target,
            **_supported_kwargs(create_context, **context_options),
        )
        if context is not None:
            if getattr(context, "model_hint", None) is None and row.model_hint is not None:
                _set_context_attribute(context, "model_hint", row.model_hint)
                if hasattr(context, "report"):
                    _set_context_attribute(
                        context, "report", context.report.with_model_hint(row.model_hint)
                    )
            _set_context_attribute(context, "model_hint_invalid", row.model_hint_invalid)
        return context

    def _remember_completed(
        self, output_rows: list[InventoryOutputRow | None]
    ) -> None:
        self._completed_rows = tuple(row for row in output_rows if row is not None)

    def _cancel_and_collect(
        self,
        executor: ThreadPoolExecutor,
        pending: dict[
            Future[InventoryOutputRow],
            tuple[int, int, str, CollectionContext | None],
        ],
        output_rows: list[InventoryOutputRow | None],
        cancel_event: threading.Event,
    ) -> None:
        """Stop queued work, close its contexts, then retain rows that already returned."""
        cancel_event.set()
        for future, (_, _, _, context) in pending.items():
            if future.cancel() and context is not None:
                context.close()
        executor.shutdown(wait=True, cancel_futures=True)
        for future, (position, row_id, ip, _context) in pending.items():
            if output_rows[position] is not None or future.cancelled():
                continue
            try:
                output_rows[position] = future.result()
            except BaseException:  # noqa: BLE001 - preserve completed outcomes at the batch boundary.
                output_rows[position] = InventoryOutputRow(
                    row_id, _unexpected_row_result(ip)
                )
        self._remember_completed(output_rows)


def _invalid_row_result(ip: str) -> CameraResult:
    return CameraResult(
        ip=ip or "N/A",
        status=CollectionStatus.FAILED,
        error_code=ErrorCode.INVALID_INPUT,
        error_message=_INVALID_ROW_MESSAGE,
        duration=0.0,
    )


def _has_tls_failure(report: object) -> bool:
    attempts = getattr(report, "attempts", ())
    return any(getattr(attempt, "error_category", None) == "TLS_ERROR" for attempt in attempts)


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


def _supported_kwargs(callable_object, **kwargs):
    """Filter new optional keywords for compatibility with historical service fakes."""
    try:
        parameters = inspect.signature(callable_object).parameters
    except (TypeError, ValueError):
        return {}
    if any(item.kind is inspect.Parameter.VAR_KEYWORD for item in parameters.values()):
        return kwargs
    return {key: value for key, value in kwargs.items() if key in parameters}


def _set_context_attribute(context: object, name: str, value: object) -> None:
    """Keep older test doubles usable when they expose a slotted/frozen context."""
    try:
        setattr(context, name, value)
    except (AttributeError, TypeError):
        pass
