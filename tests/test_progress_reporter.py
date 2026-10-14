from __future__ import annotations

import sys
from types import ModuleType
from typing import Any

from cam_scanner.terminal.progress import ProgressReporter


def test_rich_progress_lifecycle(monkeypatch: Any) -> None:
    events: list[tuple[Any, ...]] = []

    class Column:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            events.append((type(self).__name__, args, kwargs))

    class FakeProgress:
        def __init__(self, *columns: Any, **kwargs: Any) -> None:
            events.append(("construct", columns, kwargs))

        def start(self) -> None:
            events.append(("start",))

        def add_task(self, description: str, *, total: int) -> str:
            events.append(("add_task", description, total))
            return "task-1"

        def update(self, task_id: str, **kwargs: Any) -> None:
            events.append(("update", task_id, kwargs))

        def stop(self) -> None:
            events.append(("stop",))

    rich_module = ModuleType("rich")
    progress_module = ModuleType("rich.progress")
    progress_module.BarColumn = type("BarColumn", (Column,), {})  # type: ignore[attr-defined]
    progress_module.Progress = FakeProgress  # type: ignore[attr-defined]
    progress_module.SpinnerColumn = type("SpinnerColumn", (Column,), {})  # type: ignore[attr-defined]
    progress_module.TextColumn = type("TextColumn", (Column,), {})  # type: ignore[attr-defined]
    rich_module.progress = progress_module  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "rich", rich_module)
    monkeypatch.setitem(sys.modules, "rich.progress", progress_module)

    output: list[str] = []
    reporter = ProgressReporter(output.append)
    reporter.start(2)
    reporter.advance("192.0.2.10", "OK")
    reporter.advance("192.0.2.11", "FAILED")
    reporter.finish()

    assert ("add_task", "MULTI", 2) in events
    assert ("update", "task-1", {
        "advance": 1,
        "description": "MULTI — 1/2 processadas — 1 concluídas, 0 falhas",
    }) in events
    assert ("update", "task-1", {
        "advance": 1,
        "description": "MULTI — 2/2 processadas — 1 concluídas, 1 falhas",
    }) in events
    assert events.count(("start",)) == 1
    assert events.count(("stop",)) == 1
    assert output == []


def test_text_fallback_reports_each_attempt_and_empty_input(monkeypatch: Any) -> None:
    monkeypatch.delitem(sys.modules, "rich.progress", raising=False)
    monkeypatch.setitem(sys.modules, "rich.progress", None)
    output: list[str] = []
    reporter = ProgressReporter(output.append)

    reporter.start(2)
    reporter.advance("192.0.2.10", "OK")
    reporter.advance("192.0.2.11", "FAILED")
    reporter.finish()
    reporter.start(0)
    reporter.advance("192.0.2.12", "FAILED")
    reporter.finish()

    assert output == [
        "MULTI: 50% (1/2) — 1 concluídas, 0 falhas — 192.0.2.10 — OK",
        "MULTI: 100% (2/2) — 1 concluídas, 1 falhas — 192.0.2.11 — FAILED",
        "MULTI: nenhuma linha com dados para processar.",
        "MULTI: 100% (1/0) — 0 concluídas, 1 falhas — 192.0.2.12 — FAILED",
    ]
