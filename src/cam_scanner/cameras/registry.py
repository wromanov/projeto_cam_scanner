"""Manufacturer adapter registry contract."""
from typing import Protocol


class ManufacturerAdapter(Protocol):
    def collect(self, target: object) -> object: ...


class AdapterRegistry:
    def get(self, manufacturer: str) -> ManufacturerAdapter | None:
        """Resolve an adapter by normalized name (future implementation)."""
        raise NotImplementedError
