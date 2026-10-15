"""ONVIF Media snapshot discovery with target-bound HTTP transport."""
from __future__ import annotations

import ipaddress
import logging
from collections.abc import Callable, Mapping
from typing import Any
from urllib.parse import urlsplit

import requests
from requests.auth import HTTPDigestAuth
from requests.exceptions import (
    ConnectionError,
    ConnectTimeout,
    ReadTimeout,
    RequestException,
    Timeout,
)

from cam_scanner.cameras.transport import ControlledOnvifClient, TargetRejected
from cam_scanner.domain.models import CameraTarget
from cam_scanner.snapshot.service import SnapshotCaptureError, SnapshotFailure

_MAX_IMAGE_BYTES = 8 * 1024 * 1024
_HTTP_TIMEOUT = 10


class OnvifSnapshotProvider:
    """Fetch an ONVIF Media GetSnapshotUri result without following redirects."""

    def __init__(
        self,
        client_factory: Callable[..., Any] | None = None,
        session_factory: Callable[[], Any] | None = None,
        timeout_seconds: int = _HTTP_TIMEOUT,
    ) -> None:
        self._client_factory = client_factory
        self._session_factory = session_factory or requests.Session
        self._timeout = timeout_seconds

    def capture(self, target: CameraTarget, *, context: Any = None) -> bytes:
        if context is None and self._client_factory is None:
            raise SnapshotCaptureError(SnapshotFailure.TARGET_REJECTED)
        if context is not None and not context.snapshot_eligible("ONVIF"):
            raise SnapshotCaptureError(SnapshotFailure.AUTH_REJECTED)
        _suppress_onvif_logs()
        try:
            if context is not None:
                context.check("ONVIF")
            client = self._create_client(target, context=context)
            media = client.media()
            address = getattr(getattr(media, "operator", None), "address", None)
            if context is not None:
                context.transport.authorize("onvif_media", address)
            elif not _target_http_url(address, target.ip, allowed_port=80):
                raise SnapshotCaptureError(SnapshotFailure.TARGET_REJECTED)
            profiles = media.GetProfiles()
            token = _profile_token(profiles)
            if not token:
                raise SnapshotCaptureError(SnapshotFailure.UNSUPPORTED)
            uri_response = media.GetSnapshotUri(ProfileToken=token)
            snapshot_uri = _read_field(uri_response, "Uri")
            if context is not None:
                context.transport.authorize("snapshot_onvif", snapshot_uri)
            elif not _target_http_url(snapshot_uri, target.ip, allowed_port=80):
                raise SnapshotCaptureError(SnapshotFailure.TARGET_REJECTED)
        except SnapshotCaptureError:
            raise
        except Exception as error:  # noqa: BLE001 - dependency details can contain credentials/URLs.
            raise _normalize_onvif_error(error) from None

        if context is None and self._session_factory is requests.Session:
            raise SnapshotCaptureError(SnapshotFailure.TARGET_REJECTED)
        try:
            if context is not None:
                response = context.transport.request(
                    "snapshot_onvif", "GET", snapshot_uri, source="SNAPSHOT_HTTP",
                    auth=HTTPDigestAuth(target.username, target.password),
                )
                try:
                    return _snapshot_response(response, context=context)
                finally:
                    response.close()
            with self._session_factory() as session:
                session.trust_env = False
                response = session.get(
                    snapshot_uri,
                    auth=HTTPDigestAuth(target.username, target.password),
                    allow_redirects=False,
                    stream=True,
                    timeout=self._timeout,
                    verify=True,
                )
                try:
                    return _snapshot_response(response)
                finally:
                    response.close()
        except SnapshotCaptureError:
            raise
        except TargetRejected:
            raise SnapshotCaptureError(SnapshotFailure.TARGET_REJECTED) from None
        except (ConnectTimeout, ReadTimeout, Timeout):
            raise SnapshotCaptureError(SnapshotFailure.TIMEOUT) from None
        except ConnectionError:
            raise SnapshotCaptureError(SnapshotFailure.NETWORK_ERROR) from None
        except RequestException:
            raise SnapshotCaptureError(SnapshotFailure.NETWORK_ERROR) from None
        except (OSError, ValueError):
            raise SnapshotCaptureError(SnapshotFailure.INVALID_RESPONSE) from None

    def _create_client(self, target: CameraTarget, *, context: Any = None) -> Any:
        if self._client_factory is None:
            return ControlledOnvifClient(context, authenticated=True)
        client_factory = self._client_factory
        options: dict[str, object] = {
            "host": target.ip,
            "port": 80,
            "username": target.username,
            "password": target.password,
            "http_digest": False,
            "timeout": self._timeout,
            "use_https": False,
        }
        return client_factory(**options)


def _snapshot_response(response: Any, *, context: Any = None) -> bytes:
    status = response.status_code
    if status == 401:
        raise SnapshotCaptureError(SnapshotFailure.AUTH_REJECTED)
    if status == 403:
        raise SnapshotCaptureError(SnapshotFailure.AUTHORIZATION_DENIED)
    if status in {404, 405}:
        raise SnapshotCaptureError(SnapshotFailure.UNSUPPORTED)
    if 300 <= status < 400:
        raise SnapshotCaptureError(SnapshotFailure.TARGET_REJECTED)
    if status != 200:
        raise SnapshotCaptureError(SnapshotFailure.INVALID_RESPONSE)
    length = response.headers.get("content-length")
    if length is not None and int(length) > _MAX_IMAGE_BYTES:
        raise SnapshotCaptureError(SnapshotFailure.INVALID_RESPONSE)
    return _read_limited(response.iter_content(chunk_size=65536), context=context)


def _target_http_url(value: object, target_ip: str, allowed_port: int) -> bool:
    if not isinstance(value, str) or not value or len(value) > 2048:
        return False
    try:
        parsed = urlsplit(value)
        target = ipaddress.ip_address(target_ip)
        host = parsed.hostname
        port = parsed.port or 80
        resolved = ipaddress.ip_address(host or "")
    except (ValueError, TypeError):
        return False
    return (
        parsed.scheme.casefold() == "http"
        and parsed.username is None
        and parsed.password is None
        and parsed.fragment == ""
        and resolved == target
        and port == allowed_port
    )


def _read_limited(response_chunks, *, context: Any = None) -> bytes:
    body = bytearray()
    for chunk in response_chunks:
        if context is not None:
            context.check("SNAPSHOT_HTTP")
        if not isinstance(chunk, bytes):
            continue
        body.extend(chunk)
        if len(body) > _MAX_IMAGE_BYTES:
            raise SnapshotCaptureError(SnapshotFailure.INVALID_RESPONSE)
    if not body:
        raise SnapshotCaptureError(SnapshotFailure.INVALID_RESPONSE)
    return bytes(body)


def _profile_token(profiles: object) -> str | None:
    if not isinstance(profiles, (list, tuple)) or not profiles:
        return None
    token = _read_field(profiles[0], "token")
    if not isinstance(token, str) or not token or len(token) > 256:
        return None
    if any(ord(char) < 32 for char in token):
        return None
    return token


def _read_field(value: object, name: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(name)
    return getattr(value, name, None)


def _normalize_onvif_error(error: Exception) -> SnapshotCaptureError:
    chain: list[BaseException] = []
    current: BaseException | None = error
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        chain.append(current)
        original = getattr(current, "original_exception", None)
        current = (
            original
            if isinstance(original, BaseException)
            else current.__cause__ or current.__context__
        )
    for item in chain:
        folded = "".join(
            char
            for char in f"{type(item).__name__} {item}".casefold()
            if char.isalnum()
        )
        if (
            "failedauthentication" in folded
            or "notauthorized" in folded
            or "unauthorized" in folded
            or "401" in folded
        ):
            return SnapshotCaptureError(SnapshotFailure.AUTH_REJECTED)
        if "403" in folded or "authorizationdenied" in folded:
            return SnapshotCaptureError(SnapshotFailure.AUTHORIZATION_DENIED)
        if isinstance(item, (TimeoutError,)) or type(item).__name__ in {
            "ConnectTimeout",
            "ReadTimeout",
            "Timeout",
        }:
            return SnapshotCaptureError(SnapshotFailure.TIMEOUT)
        if isinstance(item, OSError) or type(item).__name__ in {"ConnectionError", "ConnectError"}:
            return SnapshotCaptureError(SnapshotFailure.NETWORK_ERROR)
    error_text = str(error).casefold()
    if (
        "not supported" in error_text
        or "operation not found" in error_text
        or "action not supported" in error_text
    ):
        return SnapshotCaptureError(SnapshotFailure.UNSUPPORTED)
    # Unrecognized SOAP/client errors may be authentication or policy faults;
    # stop fallback instead of treating them as evidence that ONVIF is absent.
    return SnapshotCaptureError(SnapshotFailure.UNEXPECTED)


def _suppress_onvif_logs() -> None:
    for logger_name in ("onvif", "zeep", "requests", "urllib3"):
        dependency_logger = logging.getLogger(logger_name)
        dependency_logger.setLevel(logging.CRITICAL + 1)
        dependency_logger.propagate = False
