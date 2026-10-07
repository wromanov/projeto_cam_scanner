"""Stable domain status and navigation vocabulary."""
from enum import StrEnum


class CollectionStatus(StrEnum):
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class MainMenuChoice(StrEnum):
    SINGLE = "1"
    MULTI = "2"
    EXIT = "3"
