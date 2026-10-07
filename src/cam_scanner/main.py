"""Canonical CLI entry point."""
from __future__ import annotations

import logging

from cam_scanner.application.controller import ApplicationController
from cam_scanner.application.inventory_service import InventoryService
from cam_scanner.application.single_workflow import SingleWorkflow
from cam_scanner.cameras.strategy import VendorFirstCollector
from cam_scanner.logging.sanitize import sanitized_traceback
from cam_scanner.logging.setup import configure_logging
from cam_scanner.terminal.ui import TerminalUI


def main() -> int:
    """Run the application menu and return a process status code."""
    ui = TerminalUI()
    logger = logging.getLogger("cam_scanner")

    try:
        logger = configure_logging()
        inventory_service = InventoryService(VendorFirstCollector(), logger=logger)
        controller = ApplicationController(ui, SingleWorkflow(ui, inventory_service))
        controller.run()
    except KeyboardInterrupt:
        ui.show_interrupted()
        return 130
    except Exception as exception:  # noqa: BLE001 - keep unexpected CLI failures off the terminal.
        diagnostic = sanitized_traceback(exception, exception.__traceback__)
        logger.error("Unexpected application diagnostic (sanitized):\n%s", diagnostic)
        ui.show_unexpected_error()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
