"""Bosch adapter placeholder; manufacturer-specific HTTP is not implemented."""


class BoschAdapter:
    def collect(self, target: object) -> object:
        """Adapter contract placeholder; makes no network requests."""
        raise NotImplementedError
