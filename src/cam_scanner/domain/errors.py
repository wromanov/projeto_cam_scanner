"""Domain exceptions and safe normalized collection error categories."""

from __future__ import annotations

import re
import socket
import ssl


def exception_chain(exception: BaseException) -> tuple[BaseException, ...]:
    """Return a bounded cause chain without formatting raw exception messages."""
    chain: list[BaseException] = []
    current: BaseException | None = exception
    seen: set[int] = set()
    while current is not None and id(current) not in seen and len(chain) < 16:
        seen.add(id(current))
        chain.append(current)
        original = getattr(current, "original_exception", None)
        current = (
            original
            if isinstance(original, BaseException)
            else current.__cause__ or current.__context__
        )
    return tuple(chain)


def normalize_collection_error(
    exception: BaseException, *, stage: str
) -> tuple[str, int | None, str | None]:
    """Classify an error using transport/protocol types and safe status/code fields only."""
    chain = exception_chain(exception)
    http_status: int | None = None
    protocol_code: str | None = None
    for item in chain:
        response = getattr(item, "response", None)
        status = getattr(response, "status_code", None)
        if type(status) is int and 100 <= status <= 599:
            http_status = status
            break

    if http_status == 401:
        return "AUTH_REJECTED", http_status, None
    if http_status == 403:
        return "AUTHORIZATION_DENIED", http_status, None
    if http_status == 404:
        return "ENDPOINT_UNSUPPORTED", http_status, None

    names = {type(item).__name__.casefold() for item in chain}
    modules = {type(item).__module__.casefold() for item in chain}
    folded_messages = tuple(str(item).casefold().replace("_", "") for item in chain)
    if http_status is None and any(
        marker in message
        for message in folded_messages
        for marker in ("notauthorized", "not authorized", "unauthorized", "authentication failed")
    ):
        return "AUTH_REJECTED", http_status, None
    if any(isinstance(item, ssl.SSLError) for item in chain) or any(
        "ssl" in name or "tls" in name for name in names
    ):
        return "TLS_ERROR", http_status, None
    if "connecttimeout" in names or any(
        isinstance(item, (TimeoutError, socket.timeout)) and stage == "CONNECT" for item in chain
    ):
        return "CONNECT_TIMEOUT", http_status, None
    if any(name in {"readtimeout", "timeout"} for name in names) or any(
        isinstance(item, (TimeoutError, socket.timeout)) for item in chain
    ):
        return "READ_TIMEOUT", http_status, None
    if any(isinstance(item, ConnectionRefusedError) for item in chain) or any(
        "connectionrefused" in name for name in names
    ):
        return "CONNECTION_REFUSED", http_status, None
    if any("unsupported" in name and "auth" in name for name in names):
        return "AUTH_MECHANISM_UNSUPPORTED", http_status, None
    if any(
        marker in name
        for name in names
        for marker in (
            "endpointnotfound",
            "operationnotfound",
            "unsupportedoperation",
            "notimplemented",
        )
    ):
        return "ENDPOINT_UNSUPPORTED", http_status, None
    if any("fault" == name or name.endswith("soapfault") for name in names) or any(
        module.startswith("zeep") for module in modules
    ):
        fault_codes: list[object] = [getattr(item, "code", None) for item in chain]
        safe_fault_names = {
            "Sender",
            "Receiver",
            "MustUnderstand",
            "VersionMismatch",
            "NotAuthorized",
            "InvalidArgVal",
            "ActionNotSupported",
            "OperationProhibited",
            "ResourceUnknown",
        }
        for value in fault_codes:
            if not isinstance(value, str) or len(value) > 64:
                continue
            prefix, separator, code = value.rpartition(":")
            if not separator:
                code = value
            if code in safe_fault_names and (
                not separator or re.fullmatch(r"[A-Za-z][A-Za-z0-9]{0,7}", prefix)
            ):
                protocol_code = value
                break
            if re.fullmatch(r"(?:0x[0-9A-Fa-f]{1,8}|E[0-9]{1,6})", value):
                protocol_code = value
                break
        lowered_codes = {
            value.casefold().replace("_", "")
            for value in fault_codes
            if isinstance(value, str)
        }
        if any("notauthorized" in value for value in lowered_codes):
            return "AUTH_REJECTED", http_status, protocol_code
        return "SOAP_FAULT", http_status, protocol_code
    if http_status is not None:
        return "HTTP_ERROR", http_status, None
    if any(isinstance(item, OSError) for item in chain) or any(
        name in {"connectionerror", "connecterror"} for name in names
    ):
        return "CONNECTION_REFUSED", http_status, None
    if any(isinstance(item, (ValueError, TypeError, KeyError)) for item in chain) and (
        stage == "PARSE"
    ):
        return "INVALID_RESPONSE", http_status, None
    if any("deadline" in name for name in names):
        return "DEADLINE_EXCEEDED", http_status, None
    return "UNEXPECTED", http_status, None


class CameraScannerError(Exception):
    """Base exception for application-level errors."""


class ConfigurationError(CameraScannerError):
    """Invalid or unsupported local configuration."""


class CollectionError(CameraScannerError):
    """A camera collection operation failed."""


class InvalidInputError(CameraScannerError):
    """The target supplied for a collection is invalid."""
