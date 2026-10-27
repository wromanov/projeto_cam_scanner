"""Offline application-level acceptance checks for the camera budget and cancellation."""
from __future__ import annotations

import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

import cam_scanner.application.multi_workflow as multi_workflow_module
import cam_scanner.snapshot.rtsp as rtsp_module
from cam_scanner.application.collection_context import CollectionContext
from cam_scanner.application.inventory_service import InventoryService
from cam_scanner.application.multi_workflow import MultiWorkflow
from cam_scanner.application.single_workflow import SingleWorkflow
from cam_scanner.cameras.manufacturers.hikvision import HikvisionAdapter
from cam_scanner.cameras.preauth import PreAuthEvidence
from cam_scanner.cameras.registry import AdapterRegistry
from cam_scanner.cameras.strategy import VendorFirstCollector
from cam_scanner.cameras.transport import TargetTransportPolicy
from cam_scanner.config.models import EffectiveConfig, TransportRule
from cam_scanner.domain.enums import CollectionStatus, MainMenuChoice
from cam_scanner.domain.models import (
    CameraResult,
    CameraTarget,
    CollectionAttempt,
    CollectionReport,
    EvidenceRecord,
)
from cam_scanner.excel.reader import ExcelInputBatch, ExcelInputRow
from cam_scanner.excel.writer import InventoryOutputRow
from cam_scanner.snapshot.rtsp import RtspFrameProvider
from cam_scanner.snapshot.service import (
    SnapshotCaptureError,
    SnapshotFailure,
    SnapshotService,
)

_TARGET = CameraTarget("192.0.2.42", "offline-user", "offline-password")


def _eligible_hikvision_fixture(collector):
    adapter = HikvisionAdapter(session_factory=lambda: None)

    if callable(getattr(collector, "collect_report", None)):
        adapter.collect_report = collector.collect_report
    else:
        def collect_report(target: CameraTarget, *, context: CollectionContext) -> CollectionReport:
            result = collector.collect(target, context=context)
            return CollectionReport.from_camera_result(result, source="VENDOR")

        adapter.collect_report = collect_report
    return adapter


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class _RecordingResource:
    def __init__(self, events: list[str], label: str = "resource-close") -> None:
        self.events = events
        self.label = label

    def close(self) -> None:
        self.events.append(self.label)


class _SnapshotProvider:
    def __init__(self, label: str, events: list[str]) -> None:
        self.label = label
        self.events = events

    def capture(self, target: CameraTarget, **_kwargs: object) -> bytes:
        self.events.append(self.label)
        return b"unused-offline-frame"


class _UnsupportedSnapshotProvider:
    def capture(self, *_args: object, **_kwargs: object) -> bytes:
        raise SnapshotCaptureError(SnapshotFailure.UNSUPPORTED)


class _WorkflowUI:
    def __init__(self, target: CameraTarget) -> None:
        self.target = target
        self.rendered = False
        self.report: CollectionReport | None = None
        self.snapshot_failure: SnapshotFailure | None = None
        self.snapshot_result: object | None = None

    def prompt_camera_target(self) -> CameraTarget:
        return self.target

    def render_report(
        self,
        report: CollectionReport,
        *,
        snapshot: object | None = None,
        **_kwargs: object,
    ) -> None:
        self.rendered = True
        self.report = report
        self.snapshot_failure = getattr(snapshot, "failure", None)
        self.snapshot_result = snapshot

    def render_result(self, *_args: object, **_kwargs: object) -> None:
        self.rendered = True

    def post_query_menu(self) -> MainMenuChoice:
        return MainMenuChoice.EXIT


class _MultiUI:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.completed: tuple[Path, int, int] | None = None

    def prompt_multi_input_path(self) -> str:
        return "memory-input.xlsx"

    def prompt_multi_output_path(self, _default: str) -> str:
        return "memory-output.xlsx"

    def show_multi_error(self, message: str) -> None:
        self.errors.append(message)

    def show_multi_complete(self, path: Path, total: int, *, failed: int) -> None:
        self.completed = (path, total, failed)


class _StaticReader:
    def __init__(self, rows: list[ExcelInputRow]) -> None:
        self.rows = rows

    def read(self, _path: str) -> ExcelInputBatch:
        return ExcelInputBatch(len(self.rows), iter(self.rows))


def _authorized_rtsp_context(
    *,
    cancel_event: threading.Event | None = None,
    camera_deadline_seconds: float = 45.0,
    clock: _Clock | None = None,
) -> CollectionContext:
    config = EffectiveConfig(transport_rules=(
        TransportRule(_TARGET.ip, "onvif_media", "http", None, 80),
        TransportRule(_TARGET.ip, "rtsp", "rtsp", None, 554),
    ), camera_soft_deadline_seconds=camera_deadline_seconds)
    context = CollectionContext(
        _TARGET,
        config,
        transport_factory=TargetTransportPolicy,
        cancel_event=cancel_event,
        clock=time.monotonic if clock is None else clock,
    )
    assert context.auth.begin("ONVIF", "initial")
    context.auth.observe_http(200, "ONVIF", authenticated=True)
    return context


def _rtsp_test_client_factory(
    uri_resolved: threading.Event | None = None,
):
    class MediaService:
        operator = SimpleNamespace(
            address=f"http://{_TARGET.ip}:80/onvif/media_service"
        )

        def GetProfiles(self) -> list[object]:
            return [SimpleNamespace(token="offline-profile")]

        def GetStreamUri(self, **_kwargs: object) -> object:
            return SimpleNamespace(Uri=f"rtsp://{_TARGET.ip}:554/offline-stream")

    class Client:
        def media(self) -> MediaService:
            if uri_resolved is not None:
                uri_resolved.set()
            return MediaService()

    return lambda **_options: Client()


class _MemoryWriter:
    def __init__(self) -> None:
        self.rows: list[InventoryOutputRow] | None = None

    def write(self, path: str | Path, rows: list[InventoryOutputRow]) -> Path:
        self.rows = rows
        return Path(path)


class _QuietProgress:
    def start(self, _total: int) -> None:
        pass

    def advance(self, _ip: str, _status: str) -> None:
        pass

    def finish(self) -> None:
        pass


def test_expired_camera_budget_stops_vendor_and_onvif_acquisition_phases() -> None:
    """Time consumed in pre-auth exhausts the shared camera deadline before acquisition."""
    events: list[str] = []
    clock = _Clock()
    config = EffectiveConfig(camera_soft_deadline_seconds=1.0)

    class Discoverer:
        def discover(self, target: CameraTarget, *, context: CollectionContext) -> PreAuthEvidence:
            events.append("preauth")
            clock.now = 1.1  # Simulate a bounded external operation consuming the row budget.
            return PreAuthEvidence(capabilities={"Manufacturer": "Hikvision"})

    class Vendor:
        def collect(self, target: CameraTarget, *, context: CollectionContext) -> CameraResult:
            events.append("vendor")
            raise AssertionError("vendor I/O must not start after the camera deadline")

    class Onvif:
        def collect_report(
            self, target: CameraTarget, *, context: CollectionContext
        ) -> CollectionReport:
            events.append("onvif")
            raise AssertionError("ONVIF I/O must not start after the camera deadline")

    registry = AdapterRegistry()
    registry.register("Hikvision", _eligible_hikvision_fixture(Vendor()))
    collector = VendorFirstCollector(
        onvif_collector=Onvif(), registry=registry, discoverer=Discoverer()
    )
    service = InventoryService(collector, config=config)
    context = CollectionContext(_TARGET, config, clock=clock)

    try:
        report = service.collect_report(_TARGET, context=context)
        assert events == ["preauth"]
        assert any(attempt.outcome == "FAILED" for attempt in report.attempts)
    finally:
        context.close()


def test_cooperative_cancel_stops_acquisition_and_snapshot_and_workflow_closes_resources() -> None:
    """Cancellation after pre-auth prevents later phases and SingleWorkflow closes the context."""
    events: list[str] = []
    resource = _RecordingResource(events)

    class Discoverer:
        def discover(self, target: CameraTarget, *, context: CollectionContext) -> PreAuthEvidence:
            events.append("preauth")
            context.register(resource)
            assert context.auth.begin("ONVIF", "initial")
            context.auth.observe_http(200, "ONVIF", authenticated=True)
            context.cancel_event.set()
            return PreAuthEvidence(capabilities={"Manufacturer": "Hikvision"})

    class Vendor:
        def collect(self, target: CameraTarget, *, context: CollectionContext) -> CameraResult:
            events.append("vendor")
            raise AssertionError("vendor I/O must not start after cancellation")

    class Onvif:
        def collect_report(
            self, target: CameraTarget, *, context: CollectionContext
        ) -> CollectionReport:
            events.append("onvif")
            raise AssertionError("ONVIF I/O must not start after cancellation")

    registry = AdapterRegistry()
    registry.register("Hikvision", _eligible_hikvision_fixture(Vendor()))
    collector = VendorFirstCollector(
        onvif_collector=Onvif(), registry=registry, discoverer=Discoverer()
    )
    service = InventoryService(collector)
    snapshots = SnapshotService(
        _SnapshotProvider("snapshot-onvif", events),
        _SnapshotProvider("snapshot-vendor", events),
        _SnapshotProvider("snapshot-rtsp", events),
        image_processor=lambda data: (data, 1, 1),
    )
    ui = _WorkflowUI(_TARGET)

    assert SingleWorkflow(ui, service, snapshots).run() is MainMenuChoice.EXIT

    assert ui.rendered
    assert events == ["preauth", "resource-close"]
    assert ui.report is not None
    assert ui.report.status.value == "CANCELLED"
    assert ui.snapshot_failure is SnapshotFailure.CANCELLED


def test_cancel_during_vendor_collection_stops_fallback_and_closes_single_resources() -> None:
    events: list[str] = []
    contexts: list[CollectionContext] = []

    class Discoverer:
        def discover(
            self, _target: CameraTarget, *, context: CollectionContext
        ) -> PreAuthEvidence:
            context.check("ONVIF")
            events.append("preauth")
            return PreAuthEvidence(capabilities={"Manufacturer": "Hikvision"})

    class Vendor:
        def collect_report(
            self, _target: CameraTarget, *, context: CollectionContext
        ) -> CollectionReport:
            context.register(_RecordingResource(events, "vendor-resource-close"))
            events.append("vendor-start")
            context.cancel_event.set()
            context.check("NATIVE")
            raise AssertionError("the vendor phase must stop at its cancellation checkpoint")

    class Onvif:
        def collect_report(
            self, *_args: object, **_kwargs: object
        ) -> CollectionReport:
            events.append("onvif")
            raise AssertionError("ONVIF fallback must not start after vendor cancellation")

    class CapturingInventory(InventoryService):
        def create_context(
            self,
            target: CameraTarget,
            *,
            cancel_event: threading.Event | None = None,
            manufacturer_hint: str | None = None,
        ) -> CollectionContext:
            context = super().create_context(
                target,
                cancel_event=cancel_event,
                manufacturer_hint=manufacturer_hint,
            )
            contexts.append(context)
            return context

    registry = AdapterRegistry()
    registry.register("Hikvision", _eligible_hikvision_fixture(Vendor()))
    inventory = CapturingInventory(
        VendorFirstCollector(
            onvif_collector=Onvif(), registry=registry, discoverer=Discoverer()
        )
    )
    ui = _WorkflowUI(_TARGET)
    snapshots = SnapshotService(
        _SnapshotProvider("snapshot-onvif", events),
        _SnapshotProvider("snapshot-vendor", events),
        _SnapshotProvider("snapshot-rtsp", events),
        image_processor=lambda raw: (raw, 1, 1),
    )

    SingleWorkflow(ui, inventory, snapshots).run()

    assert events == ["preauth", "vendor-start", "vendor-resource-close"]
    assert len(contexts) == 1
    assert contexts[0].cancelled
    assert ui.report is not None and ui.report.cancelled
    assert ui.snapshot_failure is SnapshotFailure.CANCELLED


def test_inventory_keyboard_interrupt_marks_context_cancelled_before_snapshot() -> None:
    events: list[str] = []
    contexts: list[CollectionContext] = []

    class InterruptingCollector:
        def collect_report(
            self, target: CameraTarget, *, context: CollectionContext
        ) -> CollectionReport:
            contexts.append(context)
            assert context.auth.begin("ONVIF", "initial")
            context.auth.observe_http(200, "ONVIF", authenticated=True)
            context.register(_RecordingResource(events))
            raise KeyboardInterrupt

    service = InventoryService(InterruptingCollector())  # type: ignore[arg-type]
    snapshots = SnapshotService(
        _SnapshotProvider("snapshot-onvif", events),
        _SnapshotProvider("snapshot-vendor", events),
        _SnapshotProvider("snapshot-rtsp", events),
        image_processor=lambda data: (data, 1, 1),
    )
    ui = _WorkflowUI(_TARGET)

    assert SingleWorkflow(ui, service, snapshots).run() is MainMenuChoice.EXIT

    assert ui.report is not None and ui.report.cancelled
    assert ui.report.status is CollectionStatus.CANCELLED
    assert ui.snapshot_failure is SnapshotFailure.CANCELLED
    assert contexts[0].cancel_event.is_set()
    assert events == ["resource-close"]


@pytest.mark.parametrize("cancel_during", ["provider", "image_processing"])
def test_snapshot_failure_after_cooperative_cancel_is_reported_as_cancelled(
    cancel_during: str,
) -> None:
    events: list[str] = []
    context = CollectionContext(_TARGET, EffectiveConfig())
    assert context.auth.begin("ONVIF", "initial")
    context.auth.observe_http(200, "ONVIF", authenticated=True)

    class UnsupportedOnvif:
        def capture(self, target: CameraTarget, **_kwargs: object) -> bytes:
            raise SnapshotCaptureError(SnapshotFailure.UNSUPPORTED)

    class InterruptingRtsp:
        def capture(self, target: CameraTarget, **_kwargs: object) -> bytes:
            events.append("rtsp")
            context.cancel_event.set()
            raise RuntimeError("provider stopped after cancellation")

    class SuccessfulOnvif:
        def capture(self, target: CameraTarget, **_kwargs: object) -> bytes:
            events.append("onvif")
            return b"frame"

    try:
        if cancel_during == "provider":
            service = SnapshotService(
                UnsupportedOnvif(),
                _SnapshotProvider("unused-vendor", events),
                InterruptingRtsp(),
                image_processor=lambda data: (data, 1, 1),
            )
            result = service.capture_one(_TARGET, context=context)
            assert events == ["rtsp"]
            assert result.attempts[-1].method.value == "RTSP_FRAME"
        else:
            def cancel_in_image_processor(data: bytes) -> tuple[bytes, int, int]:
                context.cancel_event.set()
                raise SnapshotCaptureError(SnapshotFailure.INVALID_RESPONSE)

            service = SnapshotService(
                SuccessfulOnvif(),
                _SnapshotProvider("unused-vendor", events),
                _SnapshotProvider("unused-rtsp", events),
                image_processor=cancel_in_image_processor,
            )
            result = service.capture_one(_TARGET, context=context)
            assert events == ["onvif"]

        assert result.failure is SnapshotFailure.CANCELLED
        assert result.attempts[-1].failure is SnapshotFailure.CANCELLED
    finally:
        context.close()


def test_single_deadline_is_shared_through_vendor_onvif_snapshot_and_active_rtsp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = _Clock()
    events: list[str] = []
    phases: list[tuple[str, int, float]] = []
    contexts: list[CollectionContext] = []
    config = EffectiveConfig(
        camera_soft_deadline_seconds=1.25,
        transport_rules=(
            TransportRule(_TARGET.ip, "onvif_media", "http", None, 80),
            TransportRule(_TARGET.ip, "rtsp", "rtsp", None, 554),
        ),
    )

    def mark(phase: str, context: CollectionContext, source: str) -> None:
        context.check(source)
        phases.append((phase, id(context), context.budget.deadline))
        events.append(phase)
        clock.now += 0.1

    class Discoverer:
        def discover(
            self, _target: CameraTarget, *, context: CollectionContext
        ) -> PreAuthEvidence:
            mark("preauth", context, "ONVIF")
            return PreAuthEvidence(capabilities={"Manufacturer": "Hikvision"})

    class Vendor:
        def collect_report(
            self, _target: CameraTarget, *, context: CollectionContext
        ) -> CollectionReport:
            mark("vendor", context, "NATIVE")
            context.auth.observe_http(200, "VENDOR_HIKVISION", authenticated=True)
            return CollectionReport().with_attempt(CollectionAttempt(
                stage="HTTP", operation="vendor_identity", outcome="FAILED",
                error_category="NETWORK_ERROR",
            ))

    class Onvif:
        def collect_report(
            self, target: CameraTarget, *, context: CollectionContext
        ) -> CollectionReport:
            mark("onvif", context, "ONVIF")
            context.auth.observe_http(200, "ONVIF", authenticated=True)
            return CollectionReport.from_camera_result(CameraResult(
                ip=target.ip,
                status=CollectionStatus.SUCCESS,
                manufacturer="Hikvision",
                model="DS-KD8003-OFFLINE",
                serial="OFFLINE-RTSP-BUDGET",
            ))

    class TimedInventory(InventoryService):
        def create_context(
            self,
            target: CameraTarget,
            *,
            cancel_event: threading.Event | None = None,
            manufacturer_hint: str | None = None,
        ) -> CollectionContext:
            context = CollectionContext(
                target,
                config,
                transport_factory=TargetTransportPolicy,
                cancel_event=cancel_event,
                clock=clock,
                manufacturer_hint=manufacturer_hint,
            )
            context.register(_RecordingResource(events, "context-close"))
            contexts.append(context)
            return context

    class SnapshotFailureProvider:
        def __init__(self, name: str) -> None:
            self.name = name

        def capture(
            self, _target: CameraTarget, *, context: CollectionContext, **_kwargs: object
        ) -> bytes:
            mark(self.name, context, "SNAPSHOT_HTTP")
            raise SnapshotCaptureError(SnapshotFailure.UNSUPPORTED)

    class MediaService:
        operator = SimpleNamespace(
            address=f"http://{_TARGET.ip}:80/onvif/media_service"
        )

        def GetProfiles(self) -> list[object]:
            mark("rtsp-profiles", contexts[0], "ONVIF")
            return [SimpleNamespace(token="offline-profile")]

        def GetStreamUri(self, **_kwargs: object) -> object:
            mark("rtsp-stream-uri", contexts[0], "ONVIF")
            return SimpleNamespace(Uri=f"rtsp://{_TARGET.ip}:554/offline-stream")

    class FakeClient:
        def media(self) -> MediaService:
            return MediaService()

    class FakeImage:
        def save(self, output, *, format: str, quality: int) -> None:
            assert format == "JPEG" and quality == 80
            output.write(b"\xff\xd8\xff\xd9")

    class FakeFrame:
        width = 1
        height = 1

        def to_image(self) -> FakeImage:
            return FakeImage()

    class FakeContainer:
        def decode(self, *, video: int):
            assert video == 0
            mark("rtsp-frame", contexts[0], "RTSP_FRAME")
            yield FakeFrame()

        def close(self) -> None:
            events.append("rtsp-container-close")

    class FakeAv:
        def open(self, _uri: str, *, mode: str, options: dict[str, str], timeout):
            assert mode == "r"
            assert options["rtsp_transport"] == "tcp"
            mark("rtsp-handshake", contexts[0], "RTSP_OPEN")
            return FakeContainer()

    def rtsp_client_factory(**_options: object) -> FakeClient:
        mark("rtsp-client", contexts[0], "ONVIF")
        return FakeClient()

    monkeypatch.setattr(rtsp_module, "_RTSP_CAPTURE_ENABLED", True)
    registry = AdapterRegistry()
    registry.register("Hikvision", _eligible_hikvision_fixture(Vendor()))
    inventory = TimedInventory(
        VendorFirstCollector(
            onvif_collector=Onvif(), registry=registry, discoverer=Discoverer()
        ),
        config=config,
    )
    ui = _WorkflowUI(_TARGET)
    snapshots = SnapshotService(
        SnapshotFailureProvider("snapshot-onvif"),
        SnapshotFailureProvider("snapshot-vendor"),
        RtspFrameProvider(
            client_factory=rtsp_client_factory,
            av_module=FakeAv(),
            open_timeout_seconds=1,
            read_timeout_seconds=1,
        ),
        image_processor=lambda raw: (raw, 1, 1),
    )

    SingleWorkflow(ui, inventory, snapshots).run()

    assert [phase for phase, _, _ in phases] == [
        "preauth", "vendor", "onvif", "snapshot-onvif", "snapshot-vendor",
        "rtsp-client", "rtsp-profiles", "rtsp-stream-uri", "rtsp-handshake",
        "rtsp-frame",
    ]
    assert len({context_id for _, context_id, _ in phases}) == 1
    assert {deadline for _, _, deadline in phases} == {1.25}
    assert contexts[0].budget.started_at == 0.0
    assert contexts[0].budget.remaining("RTSP_FRAME") > 0
    assert events[-2:] == ["rtsp-container-close", "context-close"]
    assert ui.report is not None
    assert ui.report.to_camera_result(_TARGET.ip).status is CollectionStatus.SUCCESS
    assert getattr(ui.snapshot_result, "successful", False)


def test_cancel_while_rtsp_frame_provider_waits_in_queue_prevents_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rtsp_module, "_RTSP_CAPTURE_ENABLED", True)
    uri_resolved = threading.Event()
    open_calls: list[str] = []
    context = _authorized_rtsp_context()

    class WaitingLock:
        def __init__(self) -> None:
            self.waiting = threading.Event()
            self.resume = threading.Event()
            self.acquisitions = 0

        def acquire(self, *, timeout: float) -> bool:
            assert timeout == 0.1
            self.acquisitions += 1
            self.waiting.set()
            assert self.resume.wait(timeout=2)
            return False

        def release(self) -> None:
            raise AssertionError("a cancelled queue wait must not release an unowned slot")

    waiting_lock = WaitingLock()
    monkeypatch.setattr(rtsp_module, "_RTSP_CAPTURE_LOCK", waiting_lock)

    class NeverOpen:
        def open(self, *_args: object, **_kwargs: object) -> object:
            open_calls.append("open")
            raise AssertionError("queued RTSP cancellation must happen before open")

    provider = RtspFrameProvider(
        client_factory=_rtsp_test_client_factory(uri_resolved), av_module=NeverOpen()
    )
    service = SnapshotService(
        _UnsupportedSnapshotProvider(),
        _SnapshotProvider("unused-vendor", []),
        provider,
        image_processor=lambda raw: (raw, 1, 1),
    )
    results = []
    errors: list[BaseException] = []

    def capture() -> None:
        try:
            results.append(service.capture_one(
                _TARGET, manufacturer="Axis", model="M1", context=context
            ))
        except Exception as error:  # noqa: BLE001 - surface worker exceptions to the test.
            errors.append(error)

    worker = threading.Thread(target=capture)
    worker.start()
    try:
        assert uri_resolved.wait(timeout=2)
        assert waiting_lock.waiting.wait(timeout=2)
        context.cancel_event.set()
        waiting_lock.resume.set()
        worker.join(timeout=3)
        assert not worker.is_alive()
        assert errors == []
        assert results[0].failure is SnapshotFailure.CANCELLED
        assert waiting_lock.acquisitions == 1
        assert open_calls == []
    finally:
        if worker.is_alive():
            context.cancel_event.set()
            waiting_lock.resume.set()
            worker.join(timeout=3)
        context.close()


def test_rtsp_queue_wait_consumes_camera_deadline_before_handshake(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rtsp_module, "_RTSP_CAPTURE_ENABLED", True)
    clock = _Clock()
    uri_resolved = threading.Event()
    open_calls: list[str] = []
    context = _authorized_rtsp_context(camera_deadline_seconds=1.0, clock=clock)

    class ExpiringQueueLock:
        def __init__(self) -> None:
            self.acquisitions = 0

        def acquire(self, *, timeout: float) -> bool:
            assert timeout == 0.1
            self.acquisitions += 1
            clock.now = 1.01  # Simulate the bounded queue wait consuming the row budget.
            return False

        def release(self) -> None:
            raise AssertionError("an expired queue wait must not release an unowned slot")

    waiting_lock = ExpiringQueueLock()
    monkeypatch.setattr(rtsp_module, "_RTSP_CAPTURE_LOCK", waiting_lock)

    class NeverOpen:
        def open(self, *_args: object, **_kwargs: object) -> object:
            open_calls.append("open")
            raise AssertionError("RTSP handshake must not start after queue expiry")

    provider = RtspFrameProvider(
        client_factory=_rtsp_test_client_factory(uri_resolved), av_module=NeverOpen()
    )
    service = SnapshotService(
        _UnsupportedSnapshotProvider(),
        _SnapshotProvider("unused-vendor", []),
        provider,
        image_processor=lambda raw: (raw, 1, 1),
    )

    try:
        assert context.budget.remaining("RTSP_OPEN") > 0
        result = service.capture_one(
            _TARGET, manufacturer="Axis", model="M1", context=context
        )
        assert uri_resolved.is_set()
        assert waiting_lock.acquisitions == 1
        assert context.budget.remaining("RTSP_OPEN") == 0
        assert result.failure is SnapshotFailure.TIMEOUT
        assert open_calls == []
    finally:
        context.close()


@pytest.mark.parametrize("cancel_during", ["handshake", "frame"])
def test_cancel_during_active_rtsp_closes_container_and_stops_frame_processing(
    cancel_during: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rtsp_module, "_RTSP_CAPTURE_ENABLED", True)
    active = threading.Event()
    release = threading.Event()
    closed: list[bool] = []
    image_conversions: list[bool] = []
    context = _authorized_rtsp_context()

    class FakeImage:
        def save(self, *_args: object, **_kwargs: object) -> None:
            image_conversions.append(True)

    class Frame:
        width = 1
        height = 1

        def to_image(self) -> FakeImage:
            image_conversions.append(True)
            return FakeImage()

    class Container:
        def decode(self, *, video: int):
            assert video == 0
            if cancel_during == "frame":
                active.set()
                assert release.wait(timeout=3)
            yield Frame()

        def close(self) -> None:
            closed.append(True)

    class FakeAv:
        def open(self, *_args: object, **_kwargs: object) -> Container:
            if cancel_during == "handshake":
                active.set()
                assert release.wait(timeout=3)
            return Container()

    service = SnapshotService(
        _UnsupportedSnapshotProvider(),
        _SnapshotProvider("unused-vendor", []),
        RtspFrameProvider(
            client_factory=_rtsp_test_client_factory(), av_module=FakeAv()
        ),
        image_processor=lambda raw: (raw, 1, 1),
    )
    results = []
    errors: list[BaseException] = []

    def capture() -> None:
        try:
            results.append(service.capture_one(
                _TARGET, manufacturer="Axis", model="M1", context=context
            ))
        except Exception as error:  # noqa: BLE001 - surface worker exceptions to the test.
            errors.append(error)

    worker = threading.Thread(target=capture)
    worker.start()
    try:
        assert active.wait(timeout=2)
        context.cancel_event.set()
        release.set()
        worker.join(timeout=3)
        assert not worker.is_alive()
        assert errors == []
        assert results[0].failure is SnapshotFailure.CANCELLED
        assert closed == [True]
        assert image_conversions == []
    finally:
        release.set()
        if worker.is_alive():
            context.cancel_event.set()
            worker.join(timeout=3)
        context.close()


def test_multi_deadline_starts_before_queue_and_is_shared_with_snapshot() -> None:
    events: list[str] = []
    clock = _Clock()
    second_context_created = threading.Event()
    contexts: list[CollectionContext] = []
    config = EffectiveConfig(camera_soft_deadline_seconds=1.0)
    first_ip = "192.0.2.31"
    second_ip = "192.0.2.32"

    class Inventory:
        def create_context(
            self,
            target: CameraTarget,
            *,
            cancel_event: threading.Event | None = None,
            manufacturer_hint: str | None = None,
        ) -> CollectionContext:
            context = CollectionContext(
                target,
                config,
                cancel_event=cancel_event,
                clock=clock,
                manufacturer_hint=manufacturer_hint,
            )
            contexts.append(context)
            if target.ip == second_ip:
                second_context_created.set()
            return context

        def collect_execution(
            self,
            target: CameraTarget,
            *,
            context: CollectionContext,
        ) -> tuple[CollectionReport, CollectionContext]:
            context.check("ONVIF")
            events.append(f"inventory:{target.ip}:{id(context)}")
            if target.ip == first_ip:
                assert second_context_created.wait(timeout=2)
                assert context.auth.begin("ONVIF", "primary")
                context.auth.observe_http(200, "ONVIF", authenticated=True)
                clock.now = 0.75
            result = CameraResult(
                ip=target.ip,
                status=CollectionStatus.SUCCESS,
                manufacturer="Axis",
                model="M1",
                serial=f"SERIAL-{target.ip.rsplit('.', maxsplit=1)[-1]}",
            )
            return CollectionReport.from_camera_result(result), context

    class Snapshot:
        def capture(self, target: CameraTarget, *, context: CollectionContext) -> bytes:
            context.check("SNAPSHOT_HTTP")
            events.append(f"snapshot:{target.ip}:{id(context)}")
            clock.now += 0.30
            raise SnapshotCaptureError(SnapshotFailure.UNSUPPORTED)

    rows = [
        ExcelInputRow(2, first_ip, "user-one", "password-one"),
        ExcelInputRow(3, second_ip, "user-two", "password-two"),
    ]
    writer = _MemoryWriter()
    MultiWorkflow(
        _MultiUI(),
        Inventory(),  # type: ignore[arg-type]
        SnapshotService(
            Snapshot(),
            _SnapshotProvider("unused-vendor", events),
            _SnapshotProvider("rtsp", events),
            image_processor=lambda raw: (raw, 1, 1),
        ),
        excel_reader=_StaticReader(rows),  # type: ignore[arg-type]
        excel_writer=writer,  # type: ignore[arg-type]
        progress_reporter=_QuietProgress(),  # type: ignore[arg-type]
        max_workers=1,
    ).run()

    assert [context.budget.started_at for context in contexts] == [0.0, 0.0]
    assert events == [
        f"inventory:{first_ip}:{id(contexts[0])}",
        f"snapshot:{first_ip}:{id(contexts[0])}",
    ]
    assert writer.rows is not None
    assert [row.result.status for row in writer.rows] == [
        CollectionStatus.SUCCESS,
        CollectionStatus.FAILED,
    ]
    assert writer.rows[0].snapshot is not None
    assert writer.rows[0].snapshot.failure is SnapshotFailure.TIMEOUT


def test_multi_cancel_closes_active_and_queued_contexts_keeps_rows_and_skips_export(
    monkeypatch,
) -> None:
    events: list[str] = []
    second_started = threading.Event()
    contexts: dict[str, CollectionContext] = {}
    first_ip, second_ip, third_ip = "192.0.2.41", "192.0.2.42", "192.0.2.43"

    class Inventory:
        def create_context(
            self,
            target: CameraTarget,
            *,
            cancel_event: threading.Event | None = None,
            manufacturer_hint: str | None = None,
        ) -> CollectionContext:
            context = CollectionContext(
                target,
                EffectiveConfig(),
                cancel_event=cancel_event,
                manufacturer_hint=manufacturer_hint,
            )
            context.register(_RecordingResource(events, f"context-close:{target.ip}"))
            contexts[target.ip] = context
            return context

        def collect_execution(
            self,
            target: CameraTarget,
            *,
            context: CollectionContext,
        ) -> tuple[CollectionReport, CollectionContext]:
            if target.ip == first_ip:
                result = CameraResult(
                    ip=target.ip,
                    status=CollectionStatus.SUCCESS,
                    manufacturer="Axis",
                    model="M1",
                    serial="SERIAL-41",
                )
                return CollectionReport.from_camera_result(result), context
            if target.ip == third_ip:
                events.append("third-started")
                result = CameraResult(ip=target.ip, status=CollectionStatus.SUCCESS)
                return CollectionReport.from_camera_result(result), context

            context.register(_RecordingResource(events, "active-resource-close"))
            second_started.set()
            assert context.cancel_event.wait(timeout=2)
            partial = CollectionReport(
                evidence=(
                    EvidenceRecord(
                        field="manufacturer",
                        value="Axis",
                        source="VENDOR",
                        confidence="STRONG",
                        protocol="HTTP",
                        operation="GET /axis-cgi/basicdeviceinfo.cgi getAllProperties",
                    ),
                ),
                attempts=(
                    CollectionAttempt(
                        stage="MERGE",
                        operation="collect_one",
                        outcome="CANCELLED",
                    ),
                ),
                cancelled=True,
            )
            return partial, context

    rows = [
        ExcelInputRow(2, first_ip, "user-one", "password-one"),
        ExcelInputRow(3, second_ip, "user-two", "password-two"),
        ExcelInputRow(4, third_ip, "user-three", "password-three"),
    ]
    writer = _MemoryWriter()
    workflow = MultiWorkflow(
        _MultiUI(),
        Inventory(),  # type: ignore[arg-type]
        SnapshotService(),
        excel_reader=_StaticReader(rows),  # type: ignore[arg-type]
        excel_writer=writer,  # type: ignore[arg-type]
        progress_reporter=_QuietProgress(),  # type: ignore[arg-type]
        max_workers=1,
    )
    real_wait = multi_workflow_module.wait
    wait_calls = 0

    def interrupt_when_second_row_is_active(futures, *, return_when):
        nonlocal wait_calls
        wait_calls += 1
        if wait_calls == 1:
            return real_wait(futures, return_when=return_when)
        assert second_started.wait(timeout=2)
        raise KeyboardInterrupt

    monkeypatch.setattr(multi_workflow_module, "wait", interrupt_when_second_row_is_active)
    with pytest.raises(KeyboardInterrupt):
        workflow.run()

    assert writer.rows is None
    assert [row.result.status for row in workflow.completed_rows] == [
        CollectionStatus.SUCCESS,
        CollectionStatus.CANCELLED,
    ]
    assert workflow.completed_rows[0].result.serial == "SERIAL-41"
    assert workflow.completed_rows[1].result.manufacturer == "Axis"
    assert "third-started" not in events
    assert "active-resource-close" in events
    assert f"context-close:{third_ip}" in events
    assert all(context.cancel_event.is_set() for context in contexts.values())


def test_multi_worker_keyboard_interrupt_closes_context_and_preserves_finished_row() -> None:
    events: list[str] = []
    first_row_processed = threading.Event()
    first_ip, second_ip = "192.0.2.51", "192.0.2.52"
    contexts: dict[str, CollectionContext] = {}

    class Inventory:
        def create_context(
            self,
            target: CameraTarget,
            *,
            cancel_event: threading.Event | None = None,
            manufacturer_hint: str | None = None,
        ) -> CollectionContext:
            context = CollectionContext(
                target,
                EffectiveConfig(),
                cancel_event=cancel_event,
                manufacturer_hint=manufacturer_hint,
            )
            context.register(_RecordingResource(events, f"closed:{target.ip}"))
            contexts[target.ip] = context
            return context

        def collect_execution(
            self,
            target: CameraTarget,
            *,
            context: CollectionContext,
        ) -> tuple[CollectionReport, CollectionContext]:
            if target.ip == first_ip:
                return CollectionReport.from_camera_result(
                    CameraResult(
                        ip=target.ip,
                        status=CollectionStatus.SUCCESS,
                        manufacturer="Axis",
                        model="M1",
                        serial="SERIAL-51",
                    )
                ), context
            assert first_row_processed.wait(timeout=2)
            raise KeyboardInterrupt

    class Progress(_QuietProgress):
        def advance(self, ip: str, _status: str) -> None:
            if ip == first_ip:
                first_row_processed.set()

    workflow = MultiWorkflow(
        _MultiUI(),
        Inventory(),  # type: ignore[arg-type]
        SnapshotService(),
        excel_reader=_StaticReader(
            [
                ExcelInputRow(2, first_ip, "user-one", "password-one"),
                ExcelInputRow(3, second_ip, "user-two", "password-two"),
            ]
        ),  # type: ignore[arg-type]
        excel_writer=_MemoryWriter(),  # type: ignore[arg-type]
        progress_reporter=Progress(),  # type: ignore[arg-type]
        max_workers=1,
    )

    with pytest.raises(KeyboardInterrupt):
        workflow.run()

    assert [row.result.status for row in workflow.completed_rows] == [
        CollectionStatus.SUCCESS,
        CollectionStatus.FAILED,
    ]
    assert workflow.completed_rows[0].result.serial == "SERIAL-51"
    assert f"closed:{first_ip}" in events
    assert f"closed:{second_ip}" in events
    assert all(context.cancel_event.is_set() for context in contexts.values())
