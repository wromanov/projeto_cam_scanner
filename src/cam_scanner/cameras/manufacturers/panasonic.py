"""Panasonic adapter placeholder; manufacturer-specific HTTP is not implemented."""


class PanasonicAdapter:
    def collect(self, target: object) -> object:
        """Adapter contract placeholder; makes no network requests."""
        raise NotImplementedError
