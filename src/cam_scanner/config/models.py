"""Effective configuration value object."""
from dataclasses import dataclass

DEFAULT_MAX_WORKERS = 8
MIN_WORKERS = 1
MAX_WORKERS = 32


@dataclass(frozen=True, slots=True)
class EffectiveConfig:
    connect_timeout_seconds: int = 3
    request_timeout_seconds: int = 7
    onvif_budget_seconds: int = 15
    manufacturer_budget_seconds: int = 10
    camera_soft_deadline_seconds: int = 45
    default_max_workers: int = DEFAULT_MAX_WORKERS
    max_workers: int = DEFAULT_MAX_WORKERS

    def __post_init__(self) -> None:
        for value in (self.default_max_workers, self.max_workers):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not MIN_WORKERS <= value <= MAX_WORKERS
            ):
                raise ValueError("max_workers deve estar entre 1 e 32.")
