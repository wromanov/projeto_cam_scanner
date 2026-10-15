"""Documented Hikvision HTTP snapshot endpoint for its supported KD8003 family."""
from __future__ import annotations

import ipaddress
from collections.abc import Callable
from typing import Any

import requests
from requests.auth import HTTPDigestAuth
from requests.exceptions import (
    ConnectionError,
    ConnectTimeout,
    ReadTimeout,
    RequestException,
    Timeout,
)

from cam_scanner.cameras.transport import TargetRejected
from cam_scanner.domain.models import CameraTarget
from cam_scanner.snapshot.onvif import _read_limited
from cam_scanner.snapshot.service import SnapshotCaptureError, SnapshotFailure

_ENDPOINT = "/ISAPI/Streaming/channels/1/picture"
_HTTP_TIMEOUT = 10


class ManufacturerSnapshotProvider:
    """Use the documented read-only endpoint only for positively identified KD8003s."""

    def __init__(
        self,
        session_factory: Callable[[], Any] | None = None,
        timeout_seconds: int = _HTTP_TIMEOUT,
    ) -> None:
        self._session_factory = session_factory or requests.Session
        self._timeout = timeout_seconds

    def capture(
        self,
        target: CameraTarget,
        manufacturer: str | None = None,
        model: str | None = None,
        *,
        context: Any = None,
    ) -> bytes:
        if context is None and self._session_factory is requests.Session:
            raise SnapshotCaptureError(SnapshotFailure.TARGET_REJECTED)
        if context is not None and not context.snapshot_eligible("VENDOR_HIKVISION"):
            raise SnapshotCaptureError(SnapshotFailure.AUTH_REJECTED)
        if (
            not isinstance(manufacturer, str)
            or manufacturer.casefold().strip() != "hikvision"
            or not isinstance(model, str)
            or "kd8003" not in model.casefold()
        ):
            raise SnapshotCaptureError(SnapshotFailure.UNSUPPORTED)
        try:
            address = ipaddress.ip_address(target.ip)
            host = f"[{address.compressed}]" if address.version == 6 else address.compressed
        except ValueError:
            raise SnapshotCaptureError(SnapshotFailure.TARGET_REJECTED) from None
        url = (context.transport.endpoint("snapshot_vendor", path=_ENDPOINT)
               if context is not None else f"http://{host}:80{_ENDPOINT}")
        try:
            if context is not None:
                response = context.transport.request(
                    "snapshot_vendor", "GET", url, source="SNAPSHOT_HTTP",
                    auth=HTTPDigestAuth(target.username, target.password),
                )
                try:
                    return _read_response(response, context=context)
                finally:
                    response.close()
            with self._session_factory() as session:
                session.trust_env = False
                response = session.get(
                    url,
                    auth=HTTPDigestAuth(target.username, target.password),
                    allow_redirects=False,
                    stream=True,
                    timeout=self._timeout,
                    verify=True,
                )
                try:
                    return _read_response(response)
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


def _read_response(response: Any, *, context: Any = None) -> bytes:
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
    return _read_limited(response.iter_content(chunk_size=65536), context=context)
