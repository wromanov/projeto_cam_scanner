"""Canonical CLI entry point."""
from __future__ import annotations

import logging

from cam_scanner.application.controller import ApplicationController
from cam_scanner.application.inventory_service import InventoryService
from cam_scanner.application.multi_workflow import MultiWorkflow
from cam_scanner.application.single_workflow import SingleWorkflow
from cam_scanner.cameras.registry import build_default_registry
from cam_scanner.cameras.strategy import VendorFirstCollector
from cam_scanner.config.loader import load_settings
from cam_scanner.logging.sanitize import sanitized_traceback
from cam_scanner.logging.setup import close_logging, configure_logging
from cam_scanner.snapshot.service import SnapshotService
from cam_scanner.terminal.ui import TerminalUI


def main() -> int:
    """Run the application menu and return a process status code."""
    ui = TerminalUI()
    logger = logging.getLogger("cam_scanner")

    try:
        settings = load_settings()
        logger = configure_logging(config=settings)
        registry = build_default_registry()
        inventory_service = InventoryService(
            VendorFirstCollector(registry=registry), logger=logger, config=settings
        )
        snapshot_service = SnapshotService()
        controller = ApplicationController(
            ui,
            SingleWorkflow(ui, inventory_service, snapshot_service),
            MultiWorkflow(ui, inventory_service, snapshot_service, max_workers=settings.max_workers),
        )
        controller.run()
    except KeyboardInterrupt:
        ui.show_interrupted()
        return 130
    except Exception as exception:  # noqa: BLE001 - keep unexpected CLI failures off the terminal.
        diagnostic = sanitized_traceback(exception, exception.__traceback__)
        # If logging could not be initialized, Logger's last-resort handler would
        # send this diagnostic to stderr, which is the operator's terminal.
        if logger.handlers:
            logger.error("Unexpected application diagnostic (sanitized):\n%s", diagnostic)
        ui.show_unexpected_error()
        return 1
    finally:
        close_logging()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
