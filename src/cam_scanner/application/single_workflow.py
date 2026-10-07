"""Integrated one-camera workflow for the P1 vertical slice."""
from cam_scanner.application.inventory_service import InventoryService
from cam_scanner.domain.enums import MainMenuChoice
from cam_scanner.domain.models import CameraTarget
from cam_scanner.terminal.ui import TerminalUI


class SingleWorkflow:
    """Collect and render one camera, then return navigation to the controller."""

    def __init__(self, ui: TerminalUI, inventory_service: InventoryService) -> None:
        self._ui = ui
        self._inventory_service = inventory_service

    def run(self) -> MainMenuChoice:
        target: CameraTarget = self._ui.prompt_camera_target()
        result = self._inventory_service.collect_one(target)
        del target
        self._ui.render_result(result)
        return self._ui.post_query_menu()
