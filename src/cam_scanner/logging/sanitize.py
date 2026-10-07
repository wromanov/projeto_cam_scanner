"""Sanitize diagnostic text before writing it to logs or the terminal."""
from __future__ import annotations

import re
import traceback
from types import TracebackType

_AUTHORIZATION_RE = re.compile(r"(?im)(\bauthorization\s*:\s*)[^\r\n]+")
_BASIC_TOKEN_RE = re.compile(r"(?i)(\bbasic\s+)[A-Za-z0-9+/=]+")
_PASSWORD_RE = re.compile(
    r"(?i)(\b(?:password|passwd|pwd)\b\s*(?:=|:)\s*)"
    r"(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)"
)
_CREDENTIAL_URL_RE = re.compile(r"(?i)\b(https?|rtsp)://[^/@\s]+@")


def sanitize_text(value: str, sensitive_values: tuple[str, ...] = ()) -> str:
    """Redact credential patterns and any explicitly supplied secret values."""
    sanitized = _AUTHORIZATION_RE.sub(r"\1[REDACTED]", value)
    sanitized = _BASIC_TOKEN_RE.sub(r"\1[REDACTED]", sanitized)
    sanitized = _PASSWORD_RE.sub(r"\1[REDACTED]", sanitized)
    sanitized = _CREDENTIAL_URL_RE.sub(r"\1://[REDACTED]@", sanitized)
    for secret in sorted((item for item in sensitive_values if item), key=len, reverse=True):
        sanitized = re.sub(re.escape(secret), "[REDACTED]", sanitized, flags=re.IGNORECASE)
    return sanitized


def sanitized_traceback(
    exception: BaseException,
    trace: TracebackType | None,
    sensitive_values: tuple[str, ...] = (),
) -> str:
    """Format an exception for diagnostic logging after redacting credentials."""
    formatted = "".join(traceback.format_exception(type(exception), exception, trace))
    return sanitize_text(formatted, sensitive_values)
