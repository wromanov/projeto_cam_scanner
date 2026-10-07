"""Error mapping, timing, and credential-sanitization coverage for P1."""
import logging
from io import StringIO

import pytest
from onvif.utils.exceptions import ONVIFOperationException
from requests.exceptions import ConnectionError, Timeout
from zeep.exceptions import Fault

from cam_scanner.application.inventory_service import InventoryService
from cam_scanner.domain.enums import CollectionMethod, CollectionStatus, ErrorCode
from cam_scanner.domain.models import CameraResult, CameraTarget


class RaisingCollector:
    def __init__(self, exception: Exception) -> None:
        self.exception = exception
        self.called = False

    def collect(self, target: CameraTarget) -> CameraResult:
        self.called = True
        raise self.exception


@pytest.mark.parametrize(
    ("exception", "expected_code"),
    [
        (Timeout("service timed out"), ErrorCode.TIMEOUT),
        (
            ONVIFOperationException("GetDeviceInformation", Timeout("wrapped timeout")),
            ErrorCode.TIMEOUT,
        ),
        (ConnectionError("connection refused"), ErrorCode.NETWORK_ERROR),
        (
            ONVIFOperationException("GetDeviceInformation", ConnectionError("wrapped connection")),
            ErrorCode.NETWORK_ERROR,
        ),
        (Fault("NotAuthorized"), ErrorCode.AUTH_ERROR),
        (
            ONVIFOperationException("GetDeviceInformation", Fault("NotAuthorized")),
            ErrorCode.AUTH_ERROR,
        ),
        (Fault("invalid SOAP response"), ErrorCode.ONVIF_ERROR),
        (
            ONVIFOperationException("GetDeviceInformation", Fault("invalid SOAP response")),
            ErrorCode.ONVIF_ERROR,
        ),
        (RuntimeError("unexpected parser failure"), ErrorCode.UNEXPECTED_ERROR),
    ],
)
def test_collection_failures_become_controlled_camera_results(
    exception: Exception,
    expected_code: ErrorCode,
) -> None:
    collector = RaisingCollector(exception)
    result = InventoryService(collector).collect_one(
        CameraTarget(ip="192.0.2.10", username="operator", password="secret")
    )

    assert collector.called
    assert result.status is CollectionStatus.FAILED
    assert result.error_code is expected_code
    assert result.error_message
    assert result.collection_method is CollectionMethod.ONVIF
    assert isinstance(result.duration, float)
    assert result.duration >= 0
    assert "Traceback" not in result.error_message
    assert "secret" not in result.error_message


def test_invalid_input_returns_before_starting_onvif_attempt() -> None:
    collector = RaisingCollector(RuntimeError("should not be called"))
    result = InventoryService(collector).collect_one(
        CameraTarget(ip="not-an-ip", username="operator", password="secret")
    )

    assert not collector.called
    assert result.status is CollectionStatus.FAILED
    assert result.error_code is ErrorCode.INVALID_INPUT
    assert result.collection_method is None
    assert isinstance(result.duration, float)
    assert result.duration >= 0


def test_unexpected_diagnostic_is_sanitized_in_the_log() -> None:
    secret = "UniquePassphrase-123"
    diagnostic_stream = StringIO()
    logger = logging.getLogger("test-sanitized-diagnostic")
    logger.handlers.clear()
    logger.propagate = False
    handler = logging.StreamHandler(diagnostic_stream)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    collector = RaisingCollector(
        RuntimeError(
            f"password={secret}\n"
            "Authorization: Basic c2VjcmV0dG9rZW4=\n"
            f"https://operator:{secret}@camera.local/onvif"
        )
    )
    result = InventoryService(collector, logger=logger).collect_one(
        CameraTarget(ip="192.0.2.10", username="operator", password=secret)
    )
    handler.flush()

    log_text = diagnostic_stream.getvalue()
    assert result.error_code is ErrorCode.UNEXPECTED_ERROR
    assert secret not in log_text
    assert "operator" not in log_text
    assert "c2VjcmV0dG9rZW4=" not in log_text
    assert "Authorization: [REDACTED]" in log_text
    assert "https://[REDACTED]@camera.local" in log_text
    logger.removeHandler(handler)
    handler.close()


def test_success_result_uses_the_inventory_service_duration() -> None:
    class SuccessfulCollector:
        def collect(self, target: CameraTarget) -> CameraResult:
            return CameraResult(
                ip=target.ip,
                status=CollectionStatus.SUCCESS,
                collection_method=CollectionMethod.ONVIF,
            )

    result = InventoryService(SuccessfulCollector(), logger=logging.getLogger("test")).collect_one(
        CameraTarget(ip="192.0.2.10", username="operator", password="secret")
    )
    assert result.status is CollectionStatus.SUCCESS
    assert isinstance(result.duration, float)
    assert result.duration >= 0


def test_duration_uses_monotonic_seconds(monkeypatch) -> None:
    ticks = iter([101.25, 103.5])
    monkeypatch.setattr("cam_scanner.application.inventory_service.time.monotonic", lambda: next(ticks))

    class SuccessfulCollector:
        def collect(self, target: CameraTarget) -> CameraResult:
            return CameraResult(
                ip=target.ip,
                status=CollectionStatus.SUCCESS,
                collection_method=CollectionMethod.ONVIF,
            )

    result = InventoryService(SuccessfulCollector()).collect_one(
        CameraTarget(ip="192.0.2.10", username="operator", password="secret")
    )
    assert result.duration == 2.25
