"""Ordered, in-memory snapshot acquisition with bounded diagnostics."""
from __future__ import annotations

import io
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

from cam_scanner.domain.models import CameraTarget

_MAX_IMAGE_BYTES = 8 * 1024 * 1024
_MAX_IMAGE_PIXELS = 40_000_000
_THUMBNAIL_SIZE = (320, 180)
_JPEG_QUALITY = 75


class SnapshotMethod(StrEnum):
    ONVIF_HTTP = "ONVIF_HTTP"
    VENDOR_HTTP = "VENDOR_HTTP"
    RTSP_FRAME = "RTSP_FRAME"


class SnapshotFailure(StrEnum):
    UNSUPPORTED = "UNSUPPORTED"
    AUTH_REJECTED = "AUTH_REJECTED"
    AUTHORIZATION_DENIED = "AUTHORIZATION_DENIED"
    TIMEOUT = "TIMEOUT"
    NETWORK_ERROR = "NETWORK_ERROR"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    TARGET_REJECTED = "TARGET_REJECTED"
    UNEXPECTED = "UNEXPECTED"


@dataclass(frozen=True, slots=True)
class SnapshotAttempt:
    method: SnapshotMethod
    success: bool
    failure: SnapshotFailure | None = None


@dataclass(frozen=True, slots=True)
class SnapshotResult:
    """A safe thumbnail value; original response bytes and URLs are never retained."""

    jpeg_bytes: bytes | None = field(default=None, repr=False)
    method: SnapshotMethod | None = None
    width: int | None = None
    height: int | None = None
    attempts: tuple[SnapshotAttempt, ...] = ()
    failure: SnapshotFailure | None = None

    @property
    def successful(self) -> bool:
        return self.jpeg_bytes is not None and self.method is not None


class SnapshotProvider(Protocol):
    def capture(self, target: CameraTarget) -> bytes: ...


class SnapshotCaptureError(Exception):
    """Normalized provider error; messages intentionally contain no raw details."""

    def __init__(self, failure: SnapshotFailure) -> None:
        self.failure = failure
        super().__init__(failure.value)


class SnapshotService:
    """Try ONVIF HTTP, supported vendor HTTP, then one RTSP frame."""

    def __init__(
        self,
        onvif_provider: SnapshotProvider | None = None,
        manufacturer_provider: SnapshotProvider | None = None,
        rtsp_provider: SnapshotProvider | None = None,
        image_processor: Callable[[bytes], tuple[bytes, int, int]] | None = None,
    ) -> None:
        self._all_providers_injected = all(
            provider is not None for provider in
            (onvif_provider, manufacturer_provider, rtsp_provider)
        )
        if onvif_provider is None:
            from cam_scanner.snapshot.onvif import OnvifSnapshotProvider

            onvif_provider = OnvifSnapshotProvider()
        if manufacturer_provider is None:
            from cam_scanner.snapshot.manufacturer import ManufacturerSnapshotProvider

            manufacturer_provider = ManufacturerSnapshotProvider()
        if rtsp_provider is None:
            from cam_scanner.snapshot.rtsp import RtspFrameProvider

            rtsp_provider = RtspFrameProvider()
        self._providers = (
            (SnapshotMethod.ONVIF_HTTP, onvif_provider),
            (SnapshotMethod.VENDOR_HTTP, manufacturer_provider),
            (SnapshotMethod.RTSP_FRAME, rtsp_provider),
        )
        self._image_processor = image_processor or _make_thumbnail

    def capture_one(
        self,
        target: CameraTarget,
        manufacturer: str | None = None,
        model: str | None = None,
        *,
        context: Any = None,
    ) -> SnapshotResult:
        if context is None and not self._all_providers_injected:
            return SnapshotResult(failure=SnapshotFailure.TARGET_REJECTED)
        if context is not None and not (
            context.snapshot_eligible("ONVIF") or context.snapshot_eligible("VENDOR_HIKVISION")
        ):
            return SnapshotResult(failure=SnapshotFailure.AUTH_REJECTED)
        attempts: list[SnapshotAttempt] = []
        last_failure = SnapshotFailure.UNSUPPORTED
        for method, provider in self._providers:
            source = "RTSP_OPEN" if method is SnapshotMethod.RTSP_FRAME else "SNAPSHOT_HTTP"
            family = "VENDOR_HIKVISION" if method is SnapshotMethod.VENDOR_HTTP else "ONVIF"
            if context is not None:
                try:
                    context.check(source)
                except Exception:  # noqa: BLE001 - cancellation and exhaustion stop image I/O.
                    return SnapshotResult(attempts=tuple(attempts), failure=SnapshotFailure.TIMEOUT)
                if not context.snapshot_eligible(family):
                    continue
            if method is SnapshotMethod.VENDOR_HTTP and not _supports_hikvision_snapshot(
                manufacturer, model
            ):
                continue
            try:
                if method is SnapshotMethod.VENDOR_HTTP:
                    options = {"manufacturer": manufacturer, "model": model}
                    if context is not None:
                        options["context"] = context
                    raw_image = provider.capture(target, **options)
                else:
                    raw_image = (provider.capture(target, context=context)
                                 if context is not None else provider.capture(target))
                if not isinstance(raw_image, bytes) or not raw_image:
                    raise SnapshotCaptureError(SnapshotFailure.INVALID_RESPONSE)
                thumbnail, width, height = self._image_processor(raw_image)
                if (
                    not thumbnail
                    or len(thumbnail) > _MAX_IMAGE_BYTES
                    or width < 1
                    or height < 1
                    or width > _THUMBNAIL_SIZE[0]
                    or height > _THUMBNAIL_SIZE[1]
                ):
                    raise SnapshotCaptureError(SnapshotFailure.INVALID_RESPONSE)
            except SnapshotCaptureError as error:
                last_failure = error.failure
                attempts.append(SnapshotAttempt(method, False, error.failure))
                if error.failure in {
                    SnapshotFailure.AUTH_REJECTED,
                    SnapshotFailure.AUTHORIZATION_DENIED,
                    SnapshotFailure.TARGET_REJECTED,
                    SnapshotFailure.UNEXPECTED,
                }:
                    break
                continue
            except Exception:  # noqa: BLE001 - raw provider and decoder details are never exposed.
                last_failure = SnapshotFailure.INVALID_RESPONSE
                attempts.append(
                    SnapshotAttempt(method, False, SnapshotFailure.INVALID_RESPONSE)
                )
                continue
            attempts.append(SnapshotAttempt(method, True))
            return SnapshotResult(
                jpeg_bytes=thumbnail,
                method=method,
                width=width,
                height=height,
                attempts=tuple(attempts),
            )

        return SnapshotResult(attempts=tuple(attempts), failure=last_failure)


def _supports_hikvision_snapshot(manufacturer: str | None, model: str | None) -> bool:
    return (
        isinstance(manufacturer, str)
        and manufacturer.casefold().strip() == "hikvision"
        and isinstance(model, str)
        and "kd8003" in model.casefold()
    )


def _make_thumbnail(raw_image: bytes) -> tuple[bytes, int, int]:
    if len(raw_image) > _MAX_IMAGE_BYTES:
        raise SnapshotCaptureError(SnapshotFailure.INVALID_RESPONSE)
    try:
        import warnings

        from PIL import Image, ImageOps
        from PIL.Image import DecompressionBombError, DecompressionBombWarning
    except ImportError:
        raise SnapshotCaptureError(SnapshotFailure.UNEXPECTED) from None

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", DecompressionBombWarning)
            with Image.open(io.BytesIO(raw_image)) as source:
                if source.width * source.height > _MAX_IMAGE_PIXELS:
                    raise SnapshotCaptureError(SnapshotFailure.INVALID_RESPONSE)
                source.load()
                oriented = ImageOps.exif_transpose(source).convert("RGB")
                oriented.thumbnail(_THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
                # A fresh image prevents EXIF, ICC, comments, and source metadata from copying.
                clean = Image.new("RGB", oriented.size)
                clean.paste(oriented)
                output = io.BytesIO()
                clean.save(output, format="JPEG", quality=_JPEG_QUALITY, optimize=True)
                return output.getvalue(), clean.width, clean.height
    except SnapshotCaptureError:
        raise
    except (DecompressionBombError, DecompressionBombWarning, OSError, ValueError):
        raise SnapshotCaptureError(SnapshotFailure.INVALID_RESPONSE) from None
