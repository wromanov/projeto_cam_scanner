"""Domain data contracts. Password is input-only and excluded from repr."""
from dataclasses import dataclass, field
from math import isfinite

from cam_scanner.domain.enums import CollectionMethod, CollectionStatus, ErrorCode


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
    error_code: ErrorCode | None = None
    error_message: str | None = None
    collection_method: CollectionMethod | None = None
    duration: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.status, CollectionStatus):
            raise TypeError("status must use CollectionStatus")
        if self.error_code is not None and not isinstance(self.error_code, ErrorCode):
            raise TypeError("error_code must use ErrorCode")
        if self.error_message is not None and not isinstance(self.error_message, str):
            raise TypeError("error_message must be text")
        if self.collection_method is not None and not isinstance(
            self.collection_method, CollectionMethod
        ):
            raise TypeError("collection_method must use CollectionMethod")
        if type(self.duration) is not float:
            raise TypeError("duration must be a float")
        if not isfinite(self.duration) or self.duration < 0:
            raise ValueError("duration must be a finite float greater than or equal to zero")
        if self.status is CollectionStatus.SUCCESS and (
            self.error_code is not None or self.error_message is not None
        ):
            raise ValueError("successful results cannot contain error details")
        if self.status is CollectionStatus.FAILED and (
            self.error_code is None
            or not isinstance(self.error_message, str)
            or not self.error_message.strip()
        ):
            raise ValueError("failed results require an error code and message")
