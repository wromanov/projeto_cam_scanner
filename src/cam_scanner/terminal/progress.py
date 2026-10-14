"""Rich-backed progress reporting with a small text fallback for minimal installs."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any


class ProgressReporter:
    def __init__(self, output_fn: Callable[[str], object] | None = None) -> None:
        self._output = output_fn or print
        self._progress: Any | None = None
        self._task_id: Any | None = None
        self._completed = 0
        self._total = 0

    def start(self, total: int) -> None:
        self._total = max(0, total)
        self._completed = 0
        try:
            from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

            self._progress = Progress(
                SpinnerColumn(),
                TextColumn("{task.description}"),
                BarColumn(),
                TextColumn("{task.percentage:>3.0f}%"),
                transient=True,
            )
            self._progress.start()
            self._task_id = self._progress.add_task("MULTI", total=self._total)
        except ImportError:
            self._progress = None
            if self._total == 0:
                self._output("MULTI: nenhuma linha com dados para processar.")

    def advance(self, ip: str, status: str) -> None:
        self._completed += 1
        if self._progress is not None and self._task_id is not None:
            self._progress.update(
                self._task_id,
                advance=1,
                description=f"MULTI — {ip} — {status}",
            )
            return
        percent = 100 if self._total == 0 else int(self._completed * 100 / self._total)
        self._output(f"MULTI: {percent}% ({self._completed}/{self._total}) — {ip} — {status}")

    def finish(self) -> None:
        if self._progress is not None:
            self._progress.stop()
            self._progress = None
            self._task_id = None

    def render(self, value: object) -> None:
        """Keep the original boundary usable by simple callers."""
        self._output(str(value))
