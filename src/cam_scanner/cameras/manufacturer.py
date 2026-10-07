"""Normalize manufacturer names and resolve known aliases."""


_ALIASES = {
    "axis": "Axis",
    "axis communications": "Axis",
    "hikvision": "Hikvision",
    "hik": "Hikvision",
    "samsung": "Samsung/Hanwha",
    "samsung techwin": "Samsung/Hanwha",
    "hanwha": "Samsung/Hanwha",
    "dahua": "Dahua",
    "panasonic": "Panasonic",
    "bosch": "Bosch",
}


class ManufacturerNormalizer:
    def normalize(self, value: str | None) -> str | None:
        """Trim whitespace and map recognized manufacturer aliases to a family."""
        if value is None:
            return None
        normalized = " ".join(value.split())
        if not normalized:
            return None
        return _ALIASES.get(normalized.casefold(), normalized)
