"""TOML configuration loading boundary; validation is deferred."""
from cam_scanner.config.models import EffectiveConfig


def load_settings() -> EffectiveConfig:
    """Load a validated TOML configuration (future implementation)."""
    raise NotImplementedError
