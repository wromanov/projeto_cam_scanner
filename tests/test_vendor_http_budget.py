import pytest

from cam_scanner.cameras.manufacturers import _http_utils
from cam_scanner.cameras.manufacturers._http_utils import DeadlineExceeded
from cam_scanner.cameras.manufacturers.axis import AxisAdapter
from cam_scanner.cameras.manufacturers.dahua import DahuaAdapter
from cam_scanner.domain.models import CameraTarget


def test_cumulative_budget_is_checked_between_response_chunks(monkeypatch) -> None:
    clock = [0.0]
    monkeypatch.setattr(_http_utils.time, "monotonic", lambda: clock[0])

    def chunks():
        yield b"first"
        clock[0] = 10.1
        yield b"second"

    with pytest.raises(DeadlineExceeded):
        _http_utils.read_limited_until(chunks(), 1024, started=0.0, budget=10.0)


def test_request_timeout_is_bounded_by_remaining_budget(monkeypatch) -> None:
    monkeypatch.setattr(_http_utils.time, "monotonic", lambda: 4.0)

    assert _http_utils.bounded_timeout((3.0, 7.0), started=0.0, budget=6.0) == (2.0, 2.0)


class _Response:
    status_code = 200

    def __init__(self, clock: list[float]) -> None:
        self.clock = clock
        self.headers: dict[str, str] = {}

    def iter_content(self, chunk_size: int):
        del chunk_size
        yield b"first"
        self.clock[0] = 10.1
        yield b"second"

    def close(self) -> None:
        pass


class _Session:
    def __init__(self, clock: list[float]) -> None:
        self.clock = clock
        self.trust_env = True
        self.urls: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def get(self, url: str, **_kwargs):
        self.urls.append(url)
        return _Response(self.clock)

    def post(self, url: str, **_kwargs):
        self.urls.append(url)
        return _Response(self.clock)


def test_axis_reports_deadline_exhaustion_during_body_read(monkeypatch) -> None:
    clock = [0.0]
    monkeypatch.setattr(_http_utils.time, "monotonic", lambda: clock[0])
    session = _Session(clock)
    target = CameraTarget("192.0.2.10", "operator", "secret")

    report = AxisAdapter(session_factory=lambda: session).collect_report(target)

    assert len(session.urls) == 1
    assert report.attempts[-1].error_category == "DEADLINE_EXCEEDED"
    assert "secret" not in repr(report)


def test_dahua_stops_before_second_request_after_budget_expires(monkeypatch) -> None:
    clock = [0.0]
    monkeypatch.setattr(_http_utils.time, "monotonic", lambda: clock[0])
    session = _Session(clock)
    target = CameraTarget("192.0.2.10", "operator", "secret")

    report = DahuaAdapter(session_factory=lambda: session).collect_report(target)

    assert len(session.urls) == 1
    assert report.attempts[-1].error_category == "DEADLINE_EXCEEDED"
    assert "secret" not in repr(report)
