from __future__ import annotations

import logging
import os
import time
from logging.handlers import RotatingFileHandler

from cam_scanner.config.models import EffectiveConfig
from cam_scanner.logging.setup import (
    _remove_expired_logs,
    close_logging,
    configure_logging,
)


def test_logging_uses_effective_level_size_rotation_and_closes_handlers(tmp_path) -> None:
    config = EffectiveConfig(log_level="DEBUG", log_max_file_size_mb=1)
    logger = configure_logging(config, log_directory=tmp_path)
    handler = next(item for item in logger.handlers if isinstance(item, RotatingFileHandler))

    assert logger.level == logging.DEBUG
    assert handler.maxBytes == 1024 * 1024
    assert handler.backupCount >= 1
    assert handler.baseFilename.startswith(str(tmp_path))
    assert os.path.basename(handler.baseFilename).startswith("cam_scanner_")

    logger.info("before rollover")
    handler.doRollover()
    logger.info("after rollover")
    logger.info("%s", "x" * (2 * 1024 * 1024))
    handler.flush()
    assert any(path.name.endswith(".log.1") for path in tmp_path.iterdir())
    assert all(path.stat().st_size <= 1024 * 1024 for path in tmp_path.iterdir())
    assert all(b"RUN_ID=" in path.read_bytes() for path in tmp_path.iterdir())

    close_logging()
    assert handler.stream is None


def test_retention_removes_only_expired_product_logs(tmp_path) -> None:
    expired = tmp_path / "cam_scanner_20260101_120000_abcdef12.log.1"
    unrelated = tmp_path / "other_20260101.log"
    expired.write_text("expired", encoding="utf-8")
    unrelated.write_text("keep", encoding="utf-8")
    old_time = time.time() - 40 * 24 * 60 * 60
    os.utime(expired, (old_time, old_time))
    os.utime(unrelated, (old_time, old_time))

    _remove_expired_logs(tmp_path, retention_days=30)

    assert not expired.exists()
    assert unrelated.exists()
