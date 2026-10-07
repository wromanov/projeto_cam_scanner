"""TerminalUI boundary; terminal navigation is not implemented."""


class TerminalUI:
    def render(self, value: object) -> None:
        raise NotImplementedError
