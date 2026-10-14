"""TOML configuration loading boundary."""
import tomllib
from pathlib import Path

from cam_scanner.config.models import EffectiveConfig
from cam_scanner.domain.errors import ConfigurationError


def load_settings(path: str | Path | None = None) -> EffectiveConfig:
    """Load settings and validate the configured MULTI worker limit."""
    settings_path = Path(path) if path is not None else _application_root() / "config" / "settings.toml"
    try:
        with settings_path.open("rb") as source:
            settings = tomllib.load(source)
    except FileNotFoundError:
        return EffectiveConfig()
    except (OSError, tomllib.TOMLDecodeError):
        raise ConfigurationError("Não foi possível carregar config/settings.toml.") from None

    concurrency = settings.get("concurrency", {})
    if not isinstance(concurrency, dict):
        raise ConfigurationError("Configuração de concorrência inválida.")
    workers = concurrency.get("default_max_workers", EffectiveConfig().default_max_workers)
    if isinstance(workers, bool) or not isinstance(workers, int):
        raise ConfigurationError("default_max_workers deve ser um inteiro entre 1 e 32.")
    try:
        return EffectiveConfig(default_max_workers=workers, max_workers=workers)
    except ValueError:
        raise ConfigurationError("default_max_workers deve estar entre 1 e 32.") from None


def _application_root() -> Path:
    return Path(__file__).resolve().parents[3]
