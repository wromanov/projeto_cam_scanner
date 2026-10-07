"""Shared service for safe, timed collection from one camera."""
from __future__ import annotations

import ipaddress
import logging
import math
import socket
import time
from dataclasses import replace

from cam_scanner.cameras.collector import CameraCollector
from cam_scanner.domain.enums import CollectionMethod, CollectionStatus, ErrorCode
from cam_scanner.domain.errors import InvalidInputError
from cam_scanner.domain.models import CameraResult, CameraTarget
from cam_scanner.logging.sanitize import sanitized_traceback

_PUBLIC_ERROR_MESSAGES = {
    ErrorCode.INVALID_INPUT: "Dados inválidos. Verifique o endereço IP e o usuário.",
    ErrorCode.NETWORK_ERROR: "Não foi possível conectar à câmera.",
    ErrorCode.TIMEOUT: "A consulta excedeu o tempo limite.",
    ErrorCode.AUTH_ERROR: "A câmera recusou a autenticação.",
    ErrorCode.ONVIF_ERROR: "A câmera retornou um erro ONVIF.",
    ErrorCode.UNEXPECTED_ERROR: "Ocorreu um erro inesperado durante a consulta.",
}


class InventoryService:
    """Validate a target and normalize collector failures into CameraResult."""

    def __init__(self, collector: CameraCollector, logger: logging.Logger | None = None) -> None:
        self._collector = collector
        self._logger = logger or logging.getLogger("cam_scanner")

    def collect_one(self, target: CameraTarget) -> CameraResult:
        started_at = time.monotonic()
        collection_started = False
        try:
            self._validate_target(target)
            collection_started = True
            result = self._collector.collect(target)
            return replace(result, duration=self._duration_since(started_at))
        except Exception as exception:  # noqa: BLE001 - unknown failures become sanitized results.
            error_code = self._classify_exception(exception)
            duration = self._duration_since(started_at)
            self._log_failure(target, error_code, exception)
            return CameraResult(
                ip=target.ip,
                status=CollectionStatus.FAILED,
                error_code=error_code,
                error_message=_PUBLIC_ERROR_MESSAGES[error_code],
                collection_method=CollectionMethod.ONVIF if collection_started else None,
                duration=duration,
            )

    @staticmethod
    def _validate_target(target: CameraTarget) -> None:
        try:
            ipaddress.ip_address(target.ip)
        except ValueError as exception:
            raise InvalidInputError("Target IP must be a valid IPv4 or IPv6 address") from exception
        if not target.username.strip():
            raise InvalidInputError("Target username cannot be empty")
        if not isinstance(target.password, str):
            raise InvalidInputError("Target password must be text")

    @staticmethod
    def _duration_since(started_at: float) -> float:
        elapsed = float(time.monotonic() - started_at)
        if not math.isfinite(elapsed):
            return 0.0
        return max(0.0, elapsed)

    @classmethod
    def _classify_exception(cls, exception: Exception) -> ErrorCode:
        chain = cls._exception_chain(exception)
        if any(isinstance(item, InvalidInputError) for item in chain):
            return ErrorCode.INVALID_INPUT

        auth_markers = (
            "notauthorized",
            "not authorized",
            "unauthorized",
            "authentication failed",
            "invalid credentials",
            "invalid username",
            "bad credentials",
        )
        if any(
            getattr(getattr(item, "response", None), "status_code", None) in {401, 403}
            or any(marker in str(item).casefold().replace("_", "") for marker in auth_markers)
            for item in chain
        ):
            return ErrorCode.AUTH_ERROR

        if any(
            isinstance(item, (TimeoutError, socket.timeout))
            or type(item).__name__ in {"ConnectTimeout", "ReadTimeout", "Timeout"}
            for item in chain
        ):
            return ErrorCode.TIMEOUT

        if any(
            isinstance(item, OSError)
            or type(item).__name__ in {"ConnectionError", "ConnectError"}
            for item in chain
        ):
            return ErrorCode.NETWORK_ERROR

        if any(
            type(item).__module__.startswith(("zeep", "onvif"))
            or type(item).__name__ in {"Fault", "ONVIFError"}
            for item in chain
        ):
            return ErrorCode.ONVIF_ERROR
        return ErrorCode.UNEXPECTED_ERROR

    @staticmethod
    def _exception_chain(exception: Exception) -> list[BaseException]:
        chain: list[BaseException] = []
        current: BaseException | None = exception
        seen: set[int] = set()
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            chain.append(current)
            original = getattr(current, "original_exception", None)
            cause = original if isinstance(original, BaseException) else current.__cause__
            current = cause or current.__context__
        return chain

    def _log_failure(
        self,
        target: CameraTarget,
        error_code: ErrorCode,
        exception: Exception,
    ) -> None:
        safe_ip = target.ip
        try:
            ipaddress.ip_address(target.ip)
        except ValueError:
            safe_ip = "<invalid>"
        self._logger.warning("Camera collection failed: ip=%s error_code=%s", safe_ip, error_code.value)
        if error_code is ErrorCode.UNEXPECTED_ERROR:
            diagnostic = sanitized_traceback(
                exception,
                exception.__traceback__,
                sensitive_values=(target.password, target.username),
            )
            self._logger.error("Unexpected collection diagnostic (sanitized):\n%s", diagnostic)
