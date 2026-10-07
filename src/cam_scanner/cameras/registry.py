"""Registry for manufacturer adapters that are implemented and available."""
from typing import Protocol

from cam_scanner.cameras.manufacturer import ManufacturerNormalizer


class ManufacturerAdapter(Protocol):
    def collect(self, target: object) -> object: ...


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, ManufacturerAdapter] = {}
        self._normalizer = ManufacturerNormalizer()

    def register(self, manufacturer: str, adapter: ManufacturerAdapter) -> None:
        """Register a real adapter under its normalized manufacturer family."""
        normalized = self._normalizer.normalize(manufacturer)
        if normalized is None:
            raise ValueError("manufacturer must not be empty")
        self._adapters[normalized.casefold()] = adapter

    def get(self, manufacturer: str) -> ManufacturerAdapter | None:
        """Return only a registered adapter; unavailable vendors stay unregistered."""
        normalized = self._normalizer.normalize(manufacturer)
        if normalized is None:
            return None
        return self._adapters.get(normalized.casefold())
