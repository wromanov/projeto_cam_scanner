"""Minimal structural checks; they do not exercise camera functionality."""
from dataclasses import fields
from pathlib import Path
from typing import get_type_hints

from cam_scanner.domain.enums import CollectionStatus
from cam_scanner.domain.models import CameraResult, CameraTarget

ROOT = Path(__file__).resolve().parents[1]


def test_required_package_files_exist() -> None:
    required = [
        "src/cam_scanner/application/controller.py",
        "src/cam_scanner/cameras/onvif/adapter.py",
        "src/cam_scanner/snapshot/service.py",
        "src/cam_scanner/excel/reader.py",
        "src/cam_scanner/config/loader.py",
        "packaging/cam_scanner.spec",
        "docs/continuity/PROJECT_STATE.md",
    ]
    assert all((ROOT / path).is_file() for path in required)


def test_result_contract_excludes_password_and_target_repr_hides_it() -> None:
    result_fields = {item.name: item for item in fields(CameraResult)}
    assert set(result_fields) == {
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
    }
    assert "password" not in result_fields
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
    }
    password_field = next(item for item in fields(CameraTarget) if item.name == "password")
    assert password_field.repr is False
