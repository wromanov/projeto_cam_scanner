"""ProgressReporter boundary; batch progress is not implemented."""


class ProgressReporter:
    def render(self, value: object) -> None:
        raise NotImplementedError
