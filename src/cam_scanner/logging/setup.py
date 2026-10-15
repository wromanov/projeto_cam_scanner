"""User-writable, sanitized product logging with effective bounded rotation."""
from __future__ import annotations

import logging
import re
import stat
from datetime import UTC, datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from uuid import uuid4

from cam_scanner.config.loader import user_data_directory
from cam_scanner.config.models import EffectiveConfig

_LOG_FILE_PREFIX = "cam_scanner_"
_PRODUCT_LOG = re.compile(r"^cam_scanner_[0-9]{8}_[0-9]{6}_[0-9a-f]{8}\.log(?:\.[0-9]+)?$")
_ROTATION_BACKUPS = 3


class _RunIdFilter(logging.Filter):
    def __init__(self, run_id: str) -> None:
        super().__init__()
        self.run_id = run_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = self.run_id
        return True


class _BoundedFormatter(logging.Formatter):
    def __init__(self, max_bytes: int) -> None:
        super().__init__("%(asctime)s %(levelname)s RUN_ID=%(run_id)s %(message)s")
        self._record_limit = max_bytes - 1  # reserve one byte for the handler's line terminator

    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        encoded = rendered.encode("utf-8", errors="replace")
        if len(encoded) <= self._record_limit:
            return rendered
        marker = b" [TRUNCATED]"
        prefix = encoded[: max(0, self._record_limit - len(marker))]
        return prefix.decode("utf-8", errors="ignore") + marker.decode("ascii")


def configure_logging(
    config: EffectiveConfig | None = None,
    *,
    log_directory: Path | None = None,
) -> logging.Logger:
    """Configure one user-scoped run log and close handlers from earlier runs."""
    effective = config or EffectiveConfig()
    if log_directory is None:
        log_directory = user_data_directory() / "logs"
    log_directory = Path(log_directory)
    logger = logging.getLogger("cam_scanner")
    _close_handlers(logger)
    log_directory.mkdir(parents=True, exist_ok=True)
    _remove_expired_logs(log_directory, effective.log_retention_days)

    run_id = uuid4().hex[:8]
    timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    log_path = log_directory / f"{_LOG_FILE_PREFIX}{timestamp}_{run_id}.log"
    handler = RotatingFileHandler(
        log_path,
        maxBytes=effective.log_max_file_size_mb * 1024 * 1024,
        backupCount=_ROTATION_BACKUPS,
        encoding="utf-8",
    )
    max_bytes = effective.log_max_file_size_mb * 1024 * 1024
    handler.setFormatter(_BoundedFormatter(max_bytes))
    handler.addFilter(_RunIdFilter(run_id))
    logger.setLevel(getattr(logging, effective.log_level))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def close_logging() -> None:
    """Flush and close all application-owned file handlers."""
    _close_handlers(logging.getLogger("cam_scanner"))


def _close_handlers(logger: logging.Logger) -> None:
    for existing_handler in logger.handlers[:]:
        logger.removeHandler(existing_handler)
        try:
            existing_handler.flush()
        finally:
            existing_handler.close()


def _remove_expired_logs(log_directory: Path, retention_days: int) -> None:
    cutoff = datetime.now(UTC).timestamp() - timedelta(days=retention_days).total_seconds()
    for log_path in log_directory.iterdir():
        if not _PRODUCT_LOG.fullmatch(log_path.name):
            continue
        try:
            file_stat = log_path.lstat()
            if stat.S_ISREG(file_stat.st_mode) and file_stat.st_mtime < cutoff:
                log_path.unlink()
        except OSError:
            # A locked product log must not prevent the application from starting.
            continue
