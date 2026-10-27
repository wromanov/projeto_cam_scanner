"""Capture exactly one ONVIF-advertised RTSP video frame through PyAV."""
from __future__ import annotations

import io
import ipaddress
import threading
import time
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any
from urllib.parse import urlsplit

from cam_scanner.application.collection_context import CollectionDeadlineExceeded
from cam_scanner.cameras.transport import ControlledOnvifClient, TargetRejected
from cam_scanner.domain.models import CameraTarget
from cam_scanner.snapshot.onvif import (
    _normalize_onvif_error,
    _profile_token,
    _read_field,
    _suppress_onvif_logs,
)
from cam_scanner.snapshot.service import SnapshotCaptureError, SnapshotFailure

_RTSP_OPEN_TIMEOUT = 8
_RTSP_READ_TIMEOUT = 5
_MAX_FRAME_PIXELS = 40_000_000
MAX_CONCURRENT_RTSP_FRAMES = 1
_RTSP_CAPTURE_LOCK = threading.Semaphore(MAX_CONCURRENT_RTSP_FRAMES)
_RTSP_CAPTURE_ENABLED = False


class RtspFrameProvider:
    """Obtain an RTSP URI from ONVIF, validate its authority, and decode one frame."""

    def __init__(
        self,
        client_factory: Callable[..., Any] | None = None,
        av_module: Any | None = None,
        open_timeout_seconds: int = _RTSP_OPEN_TIMEOUT,
        read_timeout_seconds: int = _RTSP_READ_TIMEOUT,
    ) -> None:
        self._client_factory = client_factory
        self._av_module = av_module
        self._open_timeout = open_timeout_seconds
        self._read_timeout = read_timeout_seconds

    def capture(self, target: CameraTarget, *, context: Any = None) -> bytes:
        if not _RTSP_CAPTURE_ENABLED:
            # FFmpeg may follow RTSP redirects or SDP control URLs beyond the
            # validated initial target; keep this path closed until each
            # connection can be authorized before it is opened.
            raise SnapshotCaptureError(SnapshotFailure.TARGET_REJECTED)
        if context is None and self._client_factory is None:
            raise SnapshotCaptureError(SnapshotFailure.TARGET_REJECTED)
        if context is not None and not context.snapshot_eligible("ONVIF"):
            raise SnapshotCaptureError(SnapshotFailure.AUTH_REJECTED)
        stream_uri = self._get_stream_uri(target, context=context)
        try:
            av_module = self._av_module
            if av_module is None:
                import av as av_module

            slot = _RTSP_CAPTURE_LOCK if context is None else _cooperative_slot(context)
            with slot:
                if context is not None:
                    context.check("RTSP_OPEN")
                    open_timeout = min(self._open_timeout, context.budget.remaining("RTSP_OPEN"))
                    read_timeout = min(self._read_timeout, context.budget.remaining("RTSP_FRAME"))
                else:
                    open_timeout, read_timeout = self._open_timeout, self._read_timeout
                opened = time.monotonic()
                try:
                    if context is not None:
                        # PyAV performs the RTSP/TCP handshake outside Requests adapters.
                        context.auth.record_physical_exchange()
                    container = av_module.open(
                        stream_uri,
                        mode="r",
                        options={
                            "rtsp_transport": "tcp",
                            "user": target.username,
                            "password": target.password,
                        },
                        timeout=(open_timeout, read_timeout),
                    )
                finally:
                    if context is not None:
                        context.charge_operation("RTSP_OPEN", time.monotonic() - opened)
                try:
                    if context is not None:
                        context.check("RTSP_FRAME")
                    frame_started = time.monotonic()
                    try:
                        frame = next(container.decode(video=0), None)
                    finally:
                        if context is not None:
                            context.charge_operation("RTSP_FRAME", time.monotonic() - frame_started)
                    if context is not None:
                        context.check("RTSP_FRAME")
                    if frame is None:
                        raise SnapshotCaptureError(SnapshotFailure.INVALID_RESPONSE)
                    if (
                        frame.width < 1
                        or frame.height < 1
                        or frame.width * frame.height > _MAX_FRAME_PIXELS
                    ):
                        raise SnapshotCaptureError(SnapshotFailure.INVALID_RESPONSE)
                    output = io.BytesIO()
                    frame.to_image().save(output, format="JPEG", quality=80)
                    image_bytes = output.getvalue()
                    if not image_bytes or len(image_bytes) > 8 * 1024 * 1024:
                        raise SnapshotCaptureError(SnapshotFailure.INVALID_RESPONSE)
                    return image_bytes
                finally:
                    container.close()
        except SnapshotCaptureError:
            raise
        except CollectionDeadlineExceeded:
            raise SnapshotCaptureError(SnapshotFailure.TIMEOUT) from None
        except Exception as error:  # noqa: BLE001 - PyAV errors are not exposed or logged.
            folded = str(error).casefold().replace("_", "")
            if "401" in folded or "unauthorized" in folded:
                if context is not None:
                    context.auth.observe_http(401, "ONVIF", authenticated=True)
                raise SnapshotCaptureError(SnapshotFailure.AUTH_REJECTED) from None
            if "403" in folded or "forbidden" in folded:
                if context is not None:
                    context.auth.observe_http(403, "ONVIF", authenticated=True)
                raise SnapshotCaptureError(SnapshotFailure.AUTHORIZATION_DENIED) from None
            if "timeout" in type(error).__name__.casefold() or "timed out" in folded:
                raise SnapshotCaptureError(SnapshotFailure.TIMEOUT) from None
            raise SnapshotCaptureError(SnapshotFailure.NETWORK_ERROR) from None


    def _get_stream_uri(self, target: CameraTarget, *, context: Any = None) -> str:
        _suppress_onvif_logs()
        client_factory = self._client_factory
        options: dict[str, object] = {
            "host": target.ip,
            "port": 80,
            "username": target.username,
            "password": target.password,
            "http_digest": False,
            "timeout": _RTSP_READ_TIMEOUT,
            "use_https": False,
        }
        try:
            if context is not None:
                context.check("ONVIF")
            client = (ControlledOnvifClient(context, authenticated=True)
                      if client_factory is None else client_factory(**options))
            media = client.media()
            address = getattr(getattr(media, "operator", None), "address", None)
            if context is not None:
                context.transport.authorize("onvif_media", address)
            elif not _target_url(address, target.ip, "http", 80):
                raise SnapshotCaptureError(SnapshotFailure.TARGET_REJECTED)
            profiles = media.GetProfiles()
            token = _profile_token(profiles)
            if not token:
                raise SnapshotCaptureError(SnapshotFailure.UNSUPPORTED)
            response = media.GetStreamUri(
                StreamSetup={
                    "Stream": "RTP-Unicast",
                    "Transport": {"Protocol": "RTSP"},
                },
                ProfileToken=token,
            )
            stream_uri = _read_field(response, "Uri")
            if context is not None:
                context.transport.authorize("rtsp", stream_uri)
            elif not _target_url(stream_uri, target.ip, "rtsp", 554):
                raise SnapshotCaptureError(SnapshotFailure.TARGET_REJECTED)
            return stream_uri
        except SnapshotCaptureError:
            raise
        except TargetRejected:
            raise SnapshotCaptureError(SnapshotFailure.TARGET_REJECTED) from None
        except Exception as error:  # noqa: BLE001 - ONVIF faults may contain the URI or auth data.
            raise _normalize_onvif_error(error) from None


@contextmanager
def _cooperative_slot(context: Any):
    acquired = False
    try:
        while not acquired:
            context.check("RTSP_OPEN")
            waited = time.monotonic()
            acquired = _RTSP_CAPTURE_LOCK.acquire(timeout=0.1)
            context.charge_operation("RTSP_OPEN", time.monotonic() - waited)
        context.check("RTSP_OPEN")
        yield
    finally:
        if acquired:
            _RTSP_CAPTURE_LOCK.release()


def _target_url(value: object, target_ip: str, scheme: str, allowed_port: int) -> bool:
    if not isinstance(value, str) or not value or len(value) > 2048:
        return False
    try:
        parsed = urlsplit(value)
        target = ipaddress.ip_address(target_ip)
        host = ipaddress.ip_address(parsed.hostname or "")
        port = parsed.port or (80 if scheme == "http" else 554)
    except (TypeError, ValueError):
        return False
    return (
        parsed.scheme.casefold() == scheme
        and parsed.username is None
        and parsed.password is None
        and parsed.fragment == ""
        and host == target
        and port == allowed_port
    )
