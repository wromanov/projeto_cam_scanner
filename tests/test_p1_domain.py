"""P1 domain contracts and validation invariants."""
from dataclasses import fields
from math import nan
from typing import get_type_hints

import pytest

from cam_scanner.domain.enums import CollectionMethod, CollectionStatus, ErrorCode
from cam_scanner.domain.models import CameraResult, CameraTarget


def test_camera_result_has_exactly_the_approved_14_fields() -> None:
    assert [item.name for item in fields(CameraResult)] == [
        "ip",
        "status",
        "hostname",
        "manufacturer",
        "manufacturer_original",
        "model",
        "serial",
        "firmware",
        "hardware_id",
        "mac",
        "error_code",
        "error_message",
        "collection_method",
        "duration",
    ]
    assert get_type_hints(CameraResult) == {
        "ip": str,
        "status": CollectionStatus,
        "hostname": str | None,
        "manufacturer": str | None,
        "manufacturer_original": str | None,
        "model": str | None,
        "serial": str | None,
        "firmware": str | None,
        "hardware_id": str | None,
        "mac": str | None,
        "error_code": ErrorCode | None,
        "error_message": str | None,
        "collection_method": CollectionMethod | None,
        "duration": float,
    }
    assert "password" not in {item.name for item in fields(CameraResult)}


def test_camera_target_repr_never_shows_password() -> None:
    target = CameraTarget(ip="192.0.2.10", username="operator", password="sensitive-value")
    assert "sensitive-value" not in repr(target)
    assert "operator" in repr(target)


@pytest.mark.parametrize("duration", [nan, float("inf"), -0.1])
def test_camera_result_rejects_non_finite_negative_or_non_float_duration(
    duration: float,
) -> None:
    with pytest.raises(ValueError):
        CameraResult(ip="192.0.2.10", status=CollectionStatus.SUCCESS, duration=duration)


def test_camera_result_requires_duration_to_be_a_float() -> None:
    with pytest.raises(TypeError):
        CameraResult(ip="192.0.2.10", status=CollectionStatus.SUCCESS, duration=1)


def test_failed_camera_result_requires_error_details() -> None:
    with pytest.raises(ValueError):
        CameraResult(ip="192.0.2.10", status=CollectionStatus.FAILED)


def test_successful_camera_result_cannot_contain_error_details() -> None:
    with pytest.raises(ValueError):
        CameraResult(
            ip="192.0.2.10",
            status=CollectionStatus.SUCCESS,
            error_code=ErrorCode.ONVIF_ERROR,
            error_message="sanitized error",
        )
