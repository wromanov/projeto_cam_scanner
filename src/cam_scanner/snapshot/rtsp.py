"""Capture exactly one ONVIF-advertised RTSP video frame through PyAV."""
from __future__ import annotations

import io
import ipaddress
import threading
from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit

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
_RTSP_CAPTURE_LOCK = threading.Lock()


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

    def capture(self, target: CameraTarget) -> bytes:
        stream_uri = self._get_stream_uri(target)
        try:
            av_module = self._av_module
            if av_module is None:
                import av as av_module

            with _RTSP_CAPTURE_LOCK:
                container = av_module.open(
                    stream_uri,
                    mode="r",
                    options={
                        "rtsp_transport": "tcp",
                        "user": target.username,
                        "password": target.password,
                    },
                    timeout=(self._open_timeout, self._read_timeout),
                )
                try:
                    frame = next(container.decode(video=0), None)
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
        except Exception as error:  # noqa: BLE001 - PyAV errors are not exposed or logged.
            folded = str(error).casefold().replace("_", "")
            if "401" in folded or "unauthorized" in folded:
                raise SnapshotCaptureError(SnapshotFailure.AUTH_REJECTED) from None
            if "403" in folded or "forbidden" in folded:
                raise SnapshotCaptureError(SnapshotFailure.AUTHORIZATION_DENIED) from None
            if "timeout" in type(error).__name__.casefold() or "timed out" in folded:
                raise SnapshotCaptureError(SnapshotFailure.TIMEOUT) from None
            raise SnapshotCaptureError(SnapshotFailure.NETWORK_ERROR) from None

    def _get_stream_uri(self, target: CameraTarget) -> str:
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
        if client_factory is None:
            try:
                from onvif import CacheMode, ONVIFClient
            except ImportError:
                raise SnapshotCaptureError(SnapshotFailure.UNEXPECTED) from None
            client_factory = ONVIFClient
            options["cache"] = CacheMode.NONE
        try:
            client = client_factory(**options)
            media = client.media()
            address = getattr(getattr(media, "operator", None), "address", None)
            if not _target_url(address, target.ip, "http", 80):
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
            if not _target_url(stream_uri, target.ip, "rtsp", 554):
                raise SnapshotCaptureError(SnapshotFailure.TARGET_REJECTED)
            return stream_uri
        except SnapshotCaptureError:
            raise
        except Exception as error:  # noqa: BLE001 - ONVIF faults may contain the URI or auth data.
            raise _normalize_onvif_error(error) from None


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
