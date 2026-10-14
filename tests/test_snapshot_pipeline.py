from __future__ import annotations

import io
import threading
from types import SimpleNamespace
from typing import ClassVar

import pytest

from cam_scanner.domain.enums import CollectionStatus, MainMenuChoice
from cam_scanner.domain.models import CameraResult, CameraTarget
from cam_scanner.snapshot.manufacturer import ManufacturerSnapshotProvider
from cam_scanner.snapshot.onvif import OnvifSnapshotProvider, _target_http_url
from cam_scanner.snapshot.rtsp import RtspFrameProvider
from cam_scanner.snapshot.service import (
    SnapshotCaptureError,
    SnapshotFailure,
    SnapshotMethod,
    SnapshotService,
)

_TARGET = CameraTarget("192.0.2.10", "operator", "camera-secret")
_THUMBNAIL = b"processed-jpeg"


class FakeProvider:
    def __init__(self, label: str, events: list[str], value: bytes | Exception) -> None:
        self.label = label
        self.events = events
        self.value = value

    def capture(self, target: CameraTarget, **_context: object) -> bytes:
        self.events.append(self.label)
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


def _processor(raw: bytes) -> tuple[bytes, int, int]:
    assert raw.startswith(b"raw-")
    return _THUMBNAIL, 320, 180


def test_snapshot_order_falls_through_to_rtsp_and_returns_processed_jpeg() -> None:
    events: list[str] = []
    service = SnapshotService(
        FakeProvider("onvif", events, SnapshotCaptureError(SnapshotFailure.UNSUPPORTED)),
        FakeProvider("vendor", events, SnapshotCaptureError(SnapshotFailure.UNSUPPORTED)),
        FakeProvider("rtsp", events, b"raw-frame"),
        image_processor=_processor,
    )

    result = service.capture_one(_TARGET, manufacturer="Hikvision", model="DS-KD8003")

    assert events == ["onvif", "vendor", "rtsp"]
    assert result.successful
    assert result.method is SnapshotMethod.RTSP_FRAME
    assert result.jpeg_bytes == _THUMBNAIL
    assert [attempt.method for attempt in result.attempts] == [
        SnapshotMethod.ONVIF_HTTP,
        SnapshotMethod.VENDOR_HTTP,
        SnapshotMethod.RTSP_FRAME,
    ]


def test_authentication_rejection_stops_snapshot_fallbacks() -> None:
    events: list[str] = []
    service = SnapshotService(
        FakeProvider("onvif", events, SnapshotCaptureError(SnapshotFailure.AUTH_REJECTED)),
        FakeProvider("vendor", events, b"raw-vendor"),
        FakeProvider("rtsp", events, b"raw-frame"),
        image_processor=_processor,
    )

    result = service.capture_one(_TARGET, manufacturer="Hikvision", model="KD8003")

    assert events == ["onvif"]
    assert result.failure is SnapshotFailure.AUTH_REJECTED
    assert not result.successful


def test_onvif_failed_authentication_fault_stops_snapshot_fallbacks() -> None:
    events: list[str] = []

    class FailedAuthentication(Exception):
        pass

    def failed_client(**_options: object) -> object:
        raise FailedAuthentication("WS-UsernameToken rejected")

    service = SnapshotService(
        OnvifSnapshotProvider(client_factory=failed_client),
        FakeProvider("vendor", events, b"raw-vendor"),
        FakeProvider("rtsp", events, b"raw-frame"),
        image_processor=_processor,
    )

    result = service.capture_one(_TARGET, manufacturer="Hikvision", model="KD8003")

    assert events == []
    assert result.failure is SnapshotFailure.AUTH_REJECTED
    assert [attempt.failure for attempt in result.attempts] == [SnapshotFailure.AUTH_REJECTED]


def test_vendor_snapshot_only_runs_for_documented_hikvision_model_family() -> None:
    events: list[str] = []
    service = SnapshotService(
        FakeProvider("onvif", events, SnapshotCaptureError(SnapshotFailure.UNSUPPORTED)),
        FakeProvider("vendor", events, b"raw-vendor"),
        FakeProvider("rtsp", events, b"raw-frame"),
        image_processor=_processor,
    )

    result = service.capture_one(_TARGET, manufacturer="Hikvision", model="DS-KD8003")
    assert result.method is SnapshotMethod.VENDOR_HTTP
    assert events == ["onvif", "vendor"]

    other_events: list[str] = []
    other_service = SnapshotService(
        FakeProvider("onvif", other_events, SnapshotCaptureError(SnapshotFailure.UNSUPPORTED)),
        FakeProvider("vendor", other_events, b"raw-vendor"),
        FakeProvider("rtsp", other_events, b"raw-frame"),
        image_processor=_processor,
    )
    other_service.capture_one(_TARGET, manufacturer="Hikvision", model="DS-2CD")
    assert other_events == ["onvif", "rtsp"]


def test_onvif_snapshot_fetch_is_bound_to_target_and_disables_redirects() -> None:
    seen: dict[str, object] = {}

    class FakeMedia:
        operator = SimpleNamespace(address="http://192.0.2.10:80/onvif/media")

        def GetProfiles(self):
            return [SimpleNamespace(token="profile-1")]

        def GetSnapshotUri(self, **kwargs):
            assert kwargs == {"ProfileToken": "profile-1"}
            return SimpleNamespace(Uri="http://192.0.2.10:80/snapshot")

    class FakeClient:
        def __init__(self, **kwargs):
            seen["client_options"] = kwargs

        def media(self):
            return FakeMedia()

    class FakeResponse:
        status_code = 200
        headers: ClassVar[dict[str, str]] = {"content-length": "8"}

        def iter_content(self, chunk_size):
            assert chunk_size == 65536
            yield b"raw-jpeg"

        def close(self):
            seen["response_closed"] = True

    class FakeSession:
        trust_env = True

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            seen["session_closed"] = True

        def get(self, url, **kwargs):
            seen["url"] = url
            seen["request_options"] = kwargs
            seen["trust_env"] = self.trust_env
            return FakeResponse()

    provider = OnvifSnapshotProvider(
        client_factory=FakeClient,
        session_factory=FakeSession,
    )
    image = provider.capture(_TARGET)

    assert image == b"raw-jpeg"
    assert seen["url"] == "http://192.0.2.10:80/snapshot"
    assert seen["trust_env"] is False
    request_options = seen["request_options"]
    assert request_options["allow_redirects"] is False
    assert request_options["timeout"] == 10
    assert request_options["verify"] is True
    assert request_options["auth"].username == "operator"
    assert request_options["auth"].password == "camera-secret"
    assert "camera-secret" not in repr(provider)
    assert seen["session_closed"] and seen["response_closed"]


@pytest.mark.parametrize(
    "uri",
    (
        "http://192.0.2.11:80/snapshot",
        "https://192.0.2.10:80/snapshot",
        "http://user:password@192.0.2.10:80/snapshot",
        "http://192.0.2.10:8080/snapshot",
        "http://camera.example:80/snapshot",
    ),
)
def test_onvif_snapshot_rejects_untrusted_or_changed_destinations(uri: str) -> None:
    assert not _target_http_url(uri, "192.0.2.10", allowed_port=80)


def test_vendor_provider_uses_only_documented_read_only_path_and_digest() -> None:
    seen: dict[str, object] = {}

    class FakeResponse:
        status_code = 200

        def iter_content(self, chunk_size):
            yield b"raw-jpeg"

        def close(self):
            seen["response_closed"] = True

    class FakeSession:
        trust_env = True

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            seen["session_closed"] = True

        def get(self, url, **kwargs):
            seen["url"] = url
            seen["options"] = kwargs
            seen["trust_env"] = self.trust_env
            return FakeResponse()

    provider = ManufacturerSnapshotProvider(session_factory=FakeSession)
    image = provider.capture(_TARGET, manufacturer="Hikvision", model="DS-KD8003")
    assert image == b"raw-jpeg"
    assert seen["url"] == "http://192.0.2.10:80/ISAPI/Streaming/channels/1/picture"
    options = seen["options"]
    assert options["allow_redirects"] is False
    assert options["verify"] is True
    assert options["auth"].username == "operator"
    assert options["auth"].password == "camera-secret"
    assert seen["trust_env"] is False
    assert seen["session_closed"] and seen["response_closed"]


def test_rtsp_uses_validated_onvif_uri_without_credentials_in_url_and_one_frame() -> None:
    seen: dict[str, object] = {}

    class FakeMedia:
        operator = SimpleNamespace(address="http://192.0.2.10:80/onvif/media")

        def GetProfiles(self):
            return [SimpleNamespace(token="profile-1")]

        def GetStreamUri(self, **kwargs):
            assert kwargs["ProfileToken"] == "profile-1"
            return SimpleNamespace(Uri="rtsp://192.0.2.10:554/live")

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def media(self):
            return FakeMedia()

    class FakeFrameImage:
        def save(self, output, **kwargs):
            seen["frame_quality"] = kwargs["quality"]
            output.write(b"raw-frame-jpeg")

    class FakeFrame:
        width = 640
        height = 360

        def to_image(self):
            return FakeFrameImage()

    class FakeContainer:
        def decode(self, video):
            assert video == 0
            yield FakeFrame()

        def close(self):
            seen["container_closed"] = True

    class FakeAv:
        def open(self, url, **kwargs):
            seen["stream_url"] = url
            seen["av_options"] = kwargs
            return FakeContainer()

    provider = RtspFrameProvider(client_factory=FakeClient, av_module=FakeAv())
    image = provider.capture(_TARGET)

    assert image == b"raw-frame-jpeg"
    assert seen["stream_url"] == "rtsp://192.0.2.10:554/live"
    assert "camera-secret" not in seen["stream_url"]
    assert seen["av_options"]["options"]["password"] == "camera-secret"
    assert seen["av_options"]["timeout"] == (8, 5)
    assert seen["container_closed"]


def test_rtsp_failed_authentication_fault_is_normalized_without_opening_stream() -> None:
    events: list[str] = []
    av_calls: list[str] = []

    class FailedAuthentication(Exception):
        pass

    def failed_client(**_options: object) -> object:
        raise FailedAuthentication("WS-UsernameToken rejected")

    class FakeAv:
        def open(self, *_args: object, **_kwargs: object) -> object:
            av_calls.append("open")
            raise AssertionError("RTSP must not open after ONVIF authentication rejection")

    service = SnapshotService(
        FakeProvider("onvif", events, SnapshotCaptureError(SnapshotFailure.UNSUPPORTED)),
        FakeProvider("vendor", events, SnapshotCaptureError(SnapshotFailure.UNSUPPORTED)),
        RtspFrameProvider(client_factory=failed_client, av_module=FakeAv()),
        image_processor=_processor,
    )

    result = service.capture_one(_TARGET, manufacturer="Hikvision", model="KD8003")

    assert events == ["onvif", "vendor"]
    assert av_calls == []
    assert result.failure is SnapshotFailure.AUTH_REJECTED
    assert result.attempts[-1].method is SnapshotMethod.RTSP_FRAME
    assert result.attempts[-1].failure is SnapshotFailure.AUTH_REJECTED


def test_rtsp_global_semaphore_limits_capture_and_releases_after_completion(monkeypatch) -> None:
    state = {"active": 0, "maximum": 0}
    state_lock = threading.Lock()
    first_frame_started = threading.Event()
    second_lock_attempted = threading.Event()
    release_first_frame = threading.Event()

    class ObservedSemaphore:
        def __init__(self) -> None:
            self._semaphore = threading.Semaphore(1)
            self._attempts = 0

        def __enter__(self):
            with state_lock:
                self._attempts += 1
                if self._attempts == 2:
                    second_lock_attempted.set()
            self._semaphore.acquire()
            return self

        def __exit__(self, *_args) -> None:
            self._semaphore.release()

    from cam_scanner.snapshot import rtsp as rtsp_module

    monkeypatch.setattr(rtsp_module, "_RTSP_CAPTURE_LOCK", ObservedSemaphore())

    class FakeMedia:
        operator = SimpleNamespace(address="http://192.0.2.10:80/onvif/media")

        def GetProfiles(self):
            return [SimpleNamespace(token="profile-1")]

        def GetStreamUri(self, **kwargs):
            return SimpleNamespace(Uri="rtsp://192.0.2.10:554/live")

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def media(self):
            return FakeMedia()

    class FakeFrameImage:
        def save(self, output, **kwargs):
            output.write(b"jpeg")

    class FakeFrame:
        width = 16
        height = 9

        def to_image(self):
            return FakeFrameImage()

    class FakeContainer:
        def decode(self, video):
            with state_lock:
                state["active"] += 1
                state["maximum"] = max(state["maximum"], state["active"])
            if state["maximum"] == 1 and not first_frame_started.is_set():
                first_frame_started.set()
                assert release_first_frame.wait(timeout=5)
            try:
                yield FakeFrame()
            finally:
                with state_lock:
                    state["active"] -= 1

        def close(self):
            pass

    class FakeAv:
        def open(self, _url, **_kwargs):
            return FakeContainer()

    provider = RtspFrameProvider(client_factory=FakeClient, av_module=FakeAv())
    workers = [threading.Thread(target=provider.capture, args=(_TARGET,)) for _ in range(2)]
    workers[0].start()
    assert first_frame_started.wait(timeout=2)
    workers[1].start()
    assert second_lock_attempted.wait(timeout=2)
    release_first_frame.set()
    for worker in workers:
        worker.join(timeout=2)

    assert all(not worker.is_alive() for worker in workers)
    assert state["maximum"] == 1


def test_rtsp_global_semaphore_is_released_after_capture_error(monkeypatch) -> None:
    class FakeMedia:
        operator = SimpleNamespace(address="http://192.0.2.10:80/onvif/media")

        def GetProfiles(self):
            return [SimpleNamespace(token="profile-1")]

        def GetStreamUri(self, **kwargs):
            return SimpleNamespace(Uri="rtsp://192.0.2.10:554/live")

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def media(self):
            return FakeMedia()

    class FakeFrameImage:
        def save(self, output, **kwargs):
            output.write(b"jpeg")

    class FakeFrame:
        width = 16
        height = 9

        def to_image(self):
            return FakeFrameImage()

    calls = 0

    class FakeContainer:
        def decode(self, video):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("synthetic decoder error")
            yield FakeFrame()

        def close(self):
            pass

    class FakeAv:
        def open(self, _url, **_kwargs):
            return FakeContainer()

    from cam_scanner.snapshot import rtsp as rtsp_module

    monkeypatch.setattr(rtsp_module, "_RTSP_CAPTURE_LOCK", threading.Semaphore(1))
    provider = RtspFrameProvider(client_factory=FakeClient, av_module=FakeAv())

    with pytest.raises(SnapshotCaptureError):
        provider.capture(_TARGET)
    assert provider.capture(_TARGET) == b"jpeg"


def test_thumbnail_preserves_aspect_and_strips_metadata_when_pillow_is_available() -> None:
    pillow = pytest.importorskip("PIL.Image")
    from cam_scanner.snapshot.service import _make_thumbnail

    source = pillow.new("RGB", (640, 320), color=(10, 20, 30))
    raw = io.BytesIO()
    source.save(raw, format="JPEG", quality=95, exif=b"Exif\x00\x00test")

    thumbnail_bytes, width, height = _make_thumbnail(raw.getvalue())

    with pillow.open(io.BytesIO(thumbnail_bytes)) as thumbnail:
        assert (width, height) == (320, 160)
        assert thumbnail.format == "JPEG"
        assert thumbnail.size == (320, 160)
        assert not thumbnail.getexif()
        assert "exif" not in thumbnail.info


def test_single_workflow_keeps_collected_identity_when_snapshot_raises() -> None:
    result = CameraResult(
        ip="192.0.2.10",
        status=CollectionStatus.PARTIAL_SUCCESS,
        manufacturer="Hikvision",
        model="DS-KD8003",
        serial="SERIAL-1",
        duration=0.1,
    )

    class FakeUI:
        rendered = None

        def prompt_camera_target(self):
            return _TARGET

        def render_result(self, camera_result, snapshot):
            self.rendered = (camera_result, snapshot)

        def post_query_menu(self):
            return MainMenuChoice.EXIT

    class FakeInventory:
        def collect_one(self, _target):
            return result

    class BrokenSnapshot:
        def capture_one(self, *_args, **_kwargs):
            raise RuntimeError("private camera-secret detail")

    from cam_scanner.application.single_workflow import SingleWorkflow

    ui = FakeUI()
    SingleWorkflow(ui, FakeInventory(), BrokenSnapshot()).run()

    assert ui.rendered[0] is result
    assert ui.rendered[1].failure is SnapshotFailure.UNEXPECTED
    assert "camera-secret" not in repr(ui.rendered[1])
