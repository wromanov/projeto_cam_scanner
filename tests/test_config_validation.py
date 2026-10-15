from __future__ import annotations

import pytest

from cam_scanner.config.loader import load_settings
from cam_scanner.config.models import EffectiveConfig, TransportRule
from cam_scanner.domain.errors import ConfigurationError


def test_embedded_defaults_and_strict_worker_schema(tmp_path) -> None:
    path = tmp_path / "settings.toml"
    path.write_text("", encoding="utf-8")

    config = load_settings(path)

    assert config.max_retries == 0
    assert config.max_workers == 8
    assert config.max_concurrent_rtsp == 1
    assert (config.thumbnail_width, config.thumbnail_height, config.jpeg_quality) == (320, 180, 75)


def test_requested_missing_settings_file_fails(tmp_path) -> None:
    with pytest.raises(ConfigurationError):
        load_settings(tmp_path / "missing.toml")


@pytest.mark.parametrize(
    "settings",
    [
        "[concurrency]\ndefault_max_workers = true\n",
        "[collection]\nconnect_timeout_seconds = 0\n",
        "[collection]\nrequest_timeout_seconds = 7.01\n",
        "[collection]\nmanufacturer_budget_seconds = nan\n",
        "[collection]\nmax_retries = 2\n",
        "[snapshot]\nstale_cleanup_hours = 24\n",
        "[unexpected]\nvalue = 1\n",
        "[logging]\nlevel = 'TRACE'\n",
        "[concurrency]\nmax_concurrent_rtsp = 2\n",
    ],
)
def test_invalid_or_obsolete_settings_fail_before_runtime(tmp_path, settings: str) -> None:
    path = tmp_path / "settings.toml"
    path.write_text(settings, encoding="utf-8")

    with pytest.raises(ConfigurationError):
        load_settings(path)


def test_transport_rules_are_exact_immutable_and_component_scoped(tmp_path) -> None:
    path = tmp_path / "settings.toml"
    path.write_text(
        "[[transport.rules]]\n"
        "target = '192.0.2.10'\n"
        "component = 'snapshot_vendor'\n"
        "protocol = 'http'\n"
        "host = '192.0.2.11'\n"
        "port = 8080\n",
        encoding="utf-8",
    )

    rules = load_settings(path).transport_rules

    assert isinstance(rules, tuple)
    assert rules == (TransportRule("192.0.2.10", "snapshot_vendor", "http", "192.0.2.11", 8080),)


@pytest.mark.parametrize(
    "rule",
    [
        "target = '192.0.2.0/24'\ncomponent = 'rtsp'\nprotocol = 'rtsp'\nport = 554\n",
        "target = '*'\ncomponent = 'rtsp'\nprotocol = 'rtsp'\nport = 554\n",
        "target = '192.0.2.10'\ncomponent = 'rtsp'\nprotocol = 'http'\nport = 80\n",
        "target = '192.0.2.10'\ncomponent = 'rtsp'\nprotocol = 'rtsp'\nport = true\n",
        "target = '192.0.2.10'\ncomponent = 'rtsp'\nprotocol = 'rtsp'\nport = 554\nextra = 1\n",
        "target = '192.0.2.10'\ncomponent = 'rtsp'\nprotocol = 'rtsp'\nhost = 'camera.local'\nport = 554\n",
    ],
)
def test_transport_wildcards_wrong_components_and_unknown_keys_fail(tmp_path, rule: str) -> None:
    path = tmp_path / "settings.toml"
    path.write_text("[[transport.rules]]\n" + rule, encoding="utf-8")

    with pytest.raises(ConfigurationError):
        load_settings(path)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"connect_timeout_seconds": True},
        {"connect_timeout_seconds": 0},
        {"request_timeout_seconds": float("inf")},
        {"max_retries": True},
        {"max_workers": 33},
        {"log_retention_days": 0},
        {"log_max_file_size_mb": 11},
    ],
)
def test_effective_config_rejects_invalid_direct_values(kwargs) -> None:
    with pytest.raises(ValueError):
        EffectiveConfig(**kwargs)
