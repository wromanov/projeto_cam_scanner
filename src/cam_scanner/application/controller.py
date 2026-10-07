"""Application navigation controller for main and post-query menus."""
from cam_scanner.application.single_workflow import SingleWorkflow
from cam_scanner.domain.enums import MainMenuChoice
from cam_scanner.terminal.ui import TerminalUI


class ApplicationController:
    """Own the application loop and dispatch workflow navigation decisions."""

    def __init__(self, ui: TerminalUI, single_workflow: SingleWorkflow) -> None:
        self._ui = ui
        self._single_workflow = single_workflow

    def run(self) -> None:
        next_action: MainMenuChoice | None = None
        while True:
            if next_action is None:
                next_action = self._ui.main_menu()

            if next_action is MainMenuChoice.EXIT:
                return
            if next_action is MainMenuChoice.MULTI:
                self._ui.show_multi_unavailable()
                next_action = None
                continue

            next_action = self._single_workflow.run()
