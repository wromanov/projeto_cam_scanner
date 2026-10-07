"""Domain data contracts. Password is input-only and excluded from repr."""
from dataclasses import dataclass, field
from cam_scanner.domain.enums import CollectionStatus


@dataclass(frozen=True, slots=True)
class CameraTarget:
    ip: str
    username: str
    password: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class CameraResult:
    """Sanitized camera output. This model intentionally has no password field."""

    ip: str
    status: CollectionStatus
    hostname: str | None = None
    manufacturer: str | None = None
    manufacturer_original: str | None = None
    model: str | None = None
    serial: str | None = None
    firmware: str | None = None
    hardware_id: str | None = None
    mac: str | None = None
