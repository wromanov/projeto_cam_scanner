"""Stable domain status and navigation vocabulary."""
from enum import StrEnum


class CollectionStatus(StrEnum):
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ErrorCode(StrEnum):
    INVALID_INPUT = "INVALID_INPUT"
    NETWORK_ERROR = "NETWORK_ERROR"
    TIMEOUT = "TIMEOUT"
    AUTH_ERROR = "AUTH_ERROR"
    ONVIF_ERROR = "ONVIF_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"


class CollectionMethod(StrEnum):
    ONVIF = "ONVIF"


class MainMenuChoice(StrEnum):
    SINGLE = "1"
    MULTI = "2"
    EXIT = "3"
