"""Manufacturer normalization contract."""


class ManufacturerNormalizer:
    def normalize(self, value: str | None) -> str | None:
        """Trim and collapse whitespace without applying vendor-specific aliases."""
        if value is None:
            return None
        normalized = " ".join(value.split())
        return normalized or None
