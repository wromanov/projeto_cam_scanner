from __future__ import annotations

import ctypes
import logging
import os
import stat
import time
from ctypes import wintypes
from datetime import UTC, timedelta
from datetime import datetime as real_datetime
from logging.handlers import RotatingFileHandler
from types import SimpleNamespace

import pytest

from cam_scanner.application.inventory_service import InventoryService
from cam_scanner.config.models import EffectiveConfig
from cam_scanner.domain.models import CameraTarget
from cam_scanner.logging import setup as logging_setup
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


def test_multibyte_records_roll_over_automatically_within_byte_limit(tmp_path) -> None:
    max_bytes = 1024 * 1024
    config = EffectiveConfig(log_level="INFO", log_max_file_size_mb=1)
    logger = configure_logging(config, log_directory=tmp_path)

    message = "é" * 300_000
    logger.info("%s", message)
    logger.info("%s", message)
    close_logging()

    product_logs = sorted(tmp_path.glob("cam_scanner_*.log*"))
    assert len(product_logs) >= 2
    assert all(path.stat().st_size <= max_bytes for path in product_logs)
    assert all(b"RUN_ID=" in path.read_bytes() for path in product_logs)


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


def test_locked_expired_product_log_does_not_block_logging(tmp_path, monkeypatch) -> None:
    expired = tmp_path / "cam_scanner_20260101_120000_abcdef12.log.1"
    unrelated = tmp_path / "keep-me.log"
    expired.write_text("old log", encoding="utf-8")
    unrelated.write_text("unrelated", encoding="utf-8")
    old_time = time.time() - 40 * 24 * 60 * 60
    os.utime(expired, (old_time, old_time))

    real_unlink = type(expired).unlink

    def unlink_with_locked_log(path, *args, **kwargs):
        if path == expired:
            raise PermissionError("simulated Windows file lock")
        return real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(type(expired), "unlink", unlink_with_locked_log)
    logger = configure_logging(
        EffectiveConfig(log_level="INFO", log_max_file_size_mb=1),
        log_directory=tmp_path,
    )
    try:
        logger.info("logging continues while an expired log is locked")
        handler = next(
            item for item in logger.handlers if isinstance(item, RotatingFileHandler)
        )
        handler.flush()
        assert b"logging continues while an expired log is locked" in (
            tmp_path / os.path.basename(handler.baseFilename)
        ).read_bytes()
        assert expired.read_text(encoding="utf-8") == "old log"
        assert unrelated.read_text(encoding="utf-8") == "unrelated"
    finally:
        close_logging()


def test_retention_uses_lstat_and_never_unlinks_a_symlink(tmp_path, monkeypatch) -> None:
    candidate = tmp_path / "cam_scanner_20260101_120000_abcdef12.log.1"
    target = tmp_path / "outside-target.log"
    candidate.write_text("simulated symlink entry", encoding="utf-8")
    target.write_text("target must remain", encoding="utf-8")
    old_time = time.time() - 40 * 24 * 60 * 60
    lstat_calls: list[str] = []
    unlink_calls: list[str] = []
    real_lstat = type(candidate).lstat

    def lstat_as_expired_symlink(path):
        if path == candidate:
            lstat_calls.append(path.name)
            return SimpleNamespace(st_mode=stat.S_IFLNK, st_mtime=old_time)
        return real_lstat(path)

    def record_unlink(path, *args, **kwargs):
        unlink_calls.append(path.name)

    monkeypatch.setattr(type(candidate), "lstat", lstat_as_expired_symlink)
    monkeypatch.setattr(type(candidate), "unlink", record_unlink)

    _remove_expired_logs(tmp_path, retention_days=30)

    assert lstat_calls == [candidate.name]
    assert unlink_calls == []
    assert candidate.read_text(encoding="utf-8") == "simulated symlink entry"
    assert target.read_text(encoding="utf-8") == "target must remain"


def test_windows_filesystem_locked_log_does_not_block_logging(tmp_path) -> None:
    assert os.name == "nt", "PREP12-11 filesystem acceptance requires Windows."
    old_time = time.time() - 40 * 24 * 60 * 60
    locked = tmp_path / "cam_scanner_20260101_120000_abcdef12.log.1"
    locked.write_text("locked log stays intact", encoding="utf-8")
    os.utime(locked, (old_time, old_time))

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.restype = wintypes.HANDLE
    kernel32.CreateFileW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel32.CreateFileW(
        str(locked),
        0x80000000,  # GENERIC_READ
        0x00000001,  # FILE_SHARE_READ; deliberately omit FILE_SHARE_DELETE
        None,
        3,  # OPEN_EXISTING
        0x00000080,  # FILE_ATTRIBUTE_NORMAL
        None,
    )
    invalid_handle = wintypes.HANDLE(-1).value
    if handle == invalid_handle:
        raise ctypes.WinError(ctypes.get_last_error())

    logger = None
    try:
        logger = configure_logging(
            EffectiveConfig(log_level="INFO", log_max_file_size_mb=1),
            log_directory=tmp_path,
        )
        logger.info("logging continues while Windows holds the prior log")

        secret = "PREP12_SENTINEL_SECRET_3f67b"

        class UnexpectedCollector:
            def collect_report(self, target: CameraTarget) -> object:
                raise RuntimeError(
                    f"password={target.password}; username={target.username}"
                )

        InventoryService(UnexpectedCollector(), logger=logger).collect_report(
            CameraTarget("192.0.2.81", "PREP12_SENTINEL_USER_54ac", secret)
        )
        handler = next(
            item for item in logger.handlers if isinstance(item, RotatingFileHandler)
        )
        handler.flush()
        active_log = tmp_path / os.path.basename(handler.baseFilename)

        assert locked.exists()
        assert locked.read_text(encoding="utf-8") == "locked log stays intact"
        assert b"logging continues while Windows holds the prior log" in active_log.read_bytes()
        assert all(
            secret.encode() not in path.read_bytes()
            and b"PREP12_SENTINEL_USER_54ac" not in path.read_bytes()
            for path in tmp_path.glob("cam_scanner_*.log*")
        )
        assert b"RuntimeError: [details omitted]" in active_log.read_bytes()
    finally:
        if logger is not None:
            close_logging()
        if not kernel32.CloseHandle(handle):
            raise ctypes.WinError(ctypes.get_last_error())


def test_windows_filesystem_retention_never_follows_real_symlink(
    tmp_path, monkeypatch
) -> None:
    assert os.name == "nt", "PREP12-11 filesystem acceptance requires Windows."
    old_time = time.time() - 40 * 24 * 60 * 60
    link = tmp_path / "cam_scanner_20260101_120001_abcdef13.log.1"
    target = tmp_path / "unrelated-target.log"
    expired_log = tmp_path / "cam_scanner_20260101_120000_deadbeef.log"
    target.write_text("symlink target stays intact", encoding="utf-8")
    expired_log.write_text("expired product log", encoding="utf-8")
    os.utime(target, (old_time, old_time))
    os.utime(expired_log, (old_time, old_time))
    try:
        os.symlink(target, link)
    except OSError as error:
        if getattr(error, "winerror", None) == 1314:
            pytest.skip("Windows symlink creation privilege is unavailable in this run.")
        raise

    class FutureDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            future = real_datetime.now(UTC) + timedelta(days=40)
            if tz is not None:
                return future.astimezone(tz)
            return future.astimezone().replace(tzinfo=None)

    monkeypatch.setattr(logging_setup, "datetime", FutureDateTime)
    retention_days = 30
    cutoff = FutureDateTime.now(UTC).timestamp() - timedelta(
        days=retention_days
    ).total_seconds()
    link_stat = link.lstat()
    assert stat.S_ISLNK(link_stat.st_mode)
    assert link_stat.st_mtime < cutoff

    try:
        configure_logging(
            EffectiveConfig(
                log_level="INFO",
                log_max_file_size_mb=1,
                log_retention_days=retention_days,
            ),
            log_directory=tmp_path,
        )
        assert not expired_log.exists()
        assert link.is_symlink()
        assert link.exists()
        assert target.read_text(encoding="utf-8") == "symlink target stays intact"
    finally:
        close_logging()
