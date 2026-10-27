"""Strict TOML loading and path resolution for development and ONEDIR runtime."""
from __future__ import annotations

import os
import sys
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from cam_scanner.config.defaults import DEFAULT_SETTINGS
from cam_scanner.config.models import EffectiveConfig, TransportRule
from cam_scanner.domain.errors import ConfigurationError

_SECTION_KEYS = {name: frozenset(values) for name, values in {
    "collection": {
        "connect_timeout_seconds", "request_timeout_seconds", "onvif_budget_seconds",
        "manufacturer_budget_seconds", "camera_soft_deadline_seconds", "max_retries",
        "retry_backoff_seconds",
    },
    "concurrency": {
        "default_max_workers", "min_workers", "max_workers", "max_concurrent_rtsp",
    },
    "snapshot": {
        "http_timeout_seconds", "rtsp_open_timeout_seconds", "rtsp_first_frame_timeout_seconds",
        "thumbnail_width", "thumbnail_height", "jpeg_quality", "keep_temporary_files",
    },
    "logging": {"level", "retention_days", "max_file_size_mb"},
    "transport": {"rules"},
}.items()}
_RULE_KEYS = frozenset({"target", "component", "protocol", "host", "port"})
_FIXED_SETTINGS = {
    ("collection", "retry_backoff_seconds"): 1,
    ("concurrency", "min_workers"): 1,
    ("concurrency", "max_workers"): 32,
    ("concurrency", "max_concurrent_rtsp"): 1,
    ("snapshot", "thumbnail_width"): 320,
    ("snapshot", "thumbnail_height"): 180,
    ("snapshot", "jpeg_quality"): 75,
    ("snapshot", "keep_temporary_files"): False,
}


def load_settings(path: str | Path | None = None) -> EffectiveConfig:
    """Load a full validated configuration; only an implicit missing file is optional."""
    requested_path = path is not None
    settings_path = Path(path).expanduser() if requested_path else _default_settings_path()
    if settings_path is None:
        raw: dict[str, Any] = {}
    else:
        try:
            with settings_path.open("rb") as source:
                raw = tomllib.load(source)
        except FileNotFoundError:
            if requested_path:
                raise ConfigurationError("O arquivo de configuração solicitado não existe.") from None
            raw = {}
        except (OSError, tomllib.TOMLDecodeError):
            raise ConfigurationError("Não foi possível carregar a configuração TOML.") from None
    if not isinstance(raw, dict):
        raise ConfigurationError("A estrutura da configuração é inválida.")
    merged = _merge_and_validate_schema(raw)
    rules = _load_transport_rules(merged["transport"]["rules"])
    concurrency = merged["concurrency"]
    workers = concurrency["default_max_workers"]
    collection = merged["collection"]
    snapshot = merged["snapshot"]
    logging = merged["logging"]
    try:
        return EffectiveConfig(
            connect_timeout_seconds=collection["connect_timeout_seconds"],
            request_timeout_seconds=collection["request_timeout_seconds"],
            onvif_budget_seconds=collection["onvif_budget_seconds"],
            manufacturer_budget_seconds=collection["manufacturer_budget_seconds"],
            camera_soft_deadline_seconds=collection["camera_soft_deadline_seconds"],
            default_max_workers=workers,
            max_workers=workers,
            max_retries=collection["max_retries"],
            snapshot_http_timeout_seconds=snapshot["http_timeout_seconds"],
            rtsp_open_timeout_seconds=snapshot["rtsp_open_timeout_seconds"],
            rtsp_first_frame_timeout_seconds=snapshot["rtsp_first_frame_timeout_seconds"],
            log_level=logging["level"],
            log_retention_days=logging["retention_days"],
            log_max_file_size_mb=logging["max_file_size_mb"],
            transport_rules=rules,
        )
    except ValueError:
        raise ConfigurationError(
            "A configuração contém valores fora dos limites aprovados."
        ) from None


def _merge_and_validate_schema(raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    unknown_sections = set(raw) - set(_SECTION_KEYS)
    if unknown_sections:
        raise ConfigurationError("A configuração contém uma seção desconhecida.")
    merged = {section: dict(values) for section, values in DEFAULT_SETTINGS.items()}
    for section, supplied in raw.items():
        if not isinstance(supplied, dict):
            raise ConfigurationError("Uma seção de configuração possui formato inválido.")
        unknown = set(supplied) - _SECTION_KEYS[section]
        if unknown:
            if "stale_cleanup_hours" in unknown:
                raise ConfigurationError("A opção obsoleta stale_cleanup_hours não é suportada.")
            raise ConfigurationError("A configuração contém uma opção desconhecida.")
        for key, value in supplied.items():
            fixed = _FIXED_SETTINGS.get((section, key))
            if fixed is not None or (section, key) in _FIXED_SETTINGS:
                if type(value) is not type(fixed) or value != fixed:
                    raise ConfigurationError("Uma opção de guardrail fixo foi alterada.")
            elif key == "rules" and section == "transport":
                if not isinstance(value, list):
                    raise ConfigurationError("transport.rules deve ser uma lista TOML.")
            elif key == "level":
                if type(value) is not str or value not in {"INFO", "DEBUG"}:
                    raise ConfigurationError("logging.level deve ser INFO ou DEBUG.")
            elif key in {"default_max_workers", "max_retries", "retention_days", "max_file_size_mb"}:
                if type(value) is not int:
                    raise ConfigurationError("Uma opção inteira possui tipo inválido.")
            elif key == "keep_temporary_files":
                if type(value) is not bool:
                    raise ConfigurationError("keep_temporary_files possui tipo inválido.")
            elif key.endswith("_seconds") and type(value) not in {int, float}:
                raise ConfigurationError("Uma opção de tempo possui tipo inválido.")
            merged[section][key] = value
    return merged


def _load_transport_rules(raw_rules: object) -> tuple[TransportRule, ...]:
    if not isinstance(raw_rules, (list, tuple)):
        raise ConfigurationError("transport.rules deve ser uma lista.")
    rules: list[TransportRule] = []
    try:
        for raw_rule in raw_rules:
            if not isinstance(raw_rule, Mapping) or set(raw_rule) - _RULE_KEYS:
                raise ValueError
            if not _RULE_KEYS - {"host"} <= set(raw_rule):
                raise ValueError
            if any(type(raw_rule[key]) is not str for key in ("target", "component", "protocol")):
                raise ValueError
            host = raw_rule.get("host")
            if host is not None and type(host) is not str:
                raise ValueError
            rules.append(TransportRule(
                target=raw_rule["target"],
                component=raw_rule["component"],
                protocol=raw_rule["protocol"],
                host=host,
                port=raw_rule["port"],
            ))
    except (KeyError, TypeError, ValueError):
        raise ConfigurationError("Uma regra de transporte é inválida.") from None
    if len(set(rules)) != len(rules):
        raise ConfigurationError("Há regras de transporte duplicadas.")
    return tuple(rules)


def user_data_directory() -> Path:
    """Return the per-user writable data root used for logs and runtime files."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "CAM Scanner"
    app_data = os.environ.get("APPDATA")
    if app_data:
        return Path(app_data) / "CAM Scanner"
    return Path.home() / "AppData" / "Local" / "CAM Scanner"


def _default_settings_path() -> Path | None:
    if getattr(sys, "frozen", False):
        # External settings are user-owned; embedded defaults remain read-only in the bundle.
        return user_data_directory() / "settings.toml"
    project_settings = _application_root() / "config" / "settings.toml"
    return project_settings if project_settings.is_file() else None


def _application_root() -> Path:
    return Path(__file__).resolve().parents[3]
