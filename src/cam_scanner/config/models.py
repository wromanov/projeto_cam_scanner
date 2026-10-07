"""Effective configuration value object."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EffectiveConfig:
    connect_timeout_seconds: int = 3
    request_timeout_seconds: int = 7
    onvif_budget_seconds: int = 15
    manufacturer_budget_seconds: int = 10
    camera_soft_deadline_seconds: int = 45
    default_max_workers: int = 8
    max_concurrent_rtsp: int = 2
