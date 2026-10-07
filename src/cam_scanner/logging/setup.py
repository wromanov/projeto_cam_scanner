"""Sanitized standard-library logging configuration for each CLI execution."""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from uuid import uuid4

_LOG_FILE_PREFIX = "cam_scanner_"


def configure_logging(log_directory: Path | None = None) -> logging.Logger:
    """Configure one bounded log file for this run, without logging credentials."""
    if log_directory is None:
        project_root = Path(__file__).resolve().parents[3]
        log_directory = project_root / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)
    _remove_expired_logs(log_directory)

    run_id = uuid4().hex[:8]
    timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    log_path = log_directory / f"{_LOG_FILE_PREFIX}{timestamp}_{run_id}.log"
    handler = RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=0,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))

    logger = logging.getLogger("cam_scanner")
    for existing_handler in logger.handlers[:]:
        logger.removeHandler(existing_handler)
        existing_handler.close()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def _remove_expired_logs(log_directory: Path) -> None:
    cutoff = datetime.now(UTC).timestamp() - timedelta(days=30).total_seconds()
    for log_path in log_directory.glob(f"{_LOG_FILE_PREFIX}*.log"):
        if log_path.is_symlink() or not log_path.is_file():
            continue
        try:
            if log_path.stat().st_mtime < cutoff:
                log_path.unlink()
        except OSError:
            # Logging must remain available even if an old file is locked.
            continue
