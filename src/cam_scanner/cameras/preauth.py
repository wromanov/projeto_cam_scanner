"""Bounded, unauthenticated ONVIF discovery and structural manufacturer resolution."""
from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from cam_scanner.cameras.manufacturer import ManufacturerNormalizer
from cam_scanner.cameras.onvif.adapter import _suppress_dependency_logs
from cam_scanner.domain.models import CameraTarget

_VENDOR_MARKERS = (
    ("hikvision", "Hikvision"),
    ("hikcapabilities", "Hikvision"),
    ("axis", "Axis"),
    ("hanwha", "Samsung/Hanwha"),
    ("samsung", "Samsung/Hanwha"),
    ("dahua", "Dahua"),
    ("panasonic", "Panasonic"),
    ("bosch", "Bosch"),
)


@dataclass(frozen=True, slots=True)
class PreAuthEvidence:
    """Successful values returned by unauthenticated, read-only ONVIF calls."""

    capabilities: object | None = None
    system_date_time: object | None = None

    @property
    def has_evidence(self) -> bool:
        return self.capabilities is not None or self.system_date_time is not None


@dataclass(frozen=True, slots=True)
class ManufacturerResolution:
    selected: str | None
    detected: str | None
    mismatch: bool


class OnvifPreAuthDiscoverer:
    """Use only anonymous ONVIF requests to obtain bounded identification evidence."""

    def __init__(
        self,
        client_factory: Callable[..., Any] | None = None,
        timeout_seconds: int = 7,
    ) -> None:
        self._client_factory = client_factory
        self._timeout_seconds = timeout_seconds

    def discover(self, target: CameraTarget) -> PreAuthEvidence:
        _suppress_dependency_logs()
        client_factory = self._client_factory
        client_options: dict[str, object] = {
            "host": target.ip,
            "port": 80,
            "timeout": self._timeout_seconds,
        }
        if client_factory is None:
            from onvif import CacheMode, ONVIFClient

            client_factory = ONVIFClient
            client_options["cache"] = CacheMode.NONE

        client = client_factory(**client_options)
        service = client.devicemgmt()
        capabilities = self._read(service, "GetCapabilities", Category="All")
        system_date_time = self._read(service, "GetSystemDateAndTime")
        return PreAuthEvidence(capabilities=capabilities, system_date_time=system_date_time)

    @staticmethod
    def _read(service: object, method_name: str, **kwargs: object) -> object | None:
        method = getattr(service, method_name, None)
        if not callable(method):
            return None
        try:
            value = method(**kwargs)
        except Exception:  # noqa: BLE001 - each bounded discovery call is independent.
            logging.getLogger("cam_scanner").debug("Unauthenticated ONVIF discovery was unavailable")
            return None
        return value if value is not None else None


class ManufacturerResolver:
    """Resolve a family from a hint or bounded public ONVIF response structure."""

    def __init__(self, normalizer: ManufacturerNormalizer | None = None) -> None:
        self._normalizer = normalizer or ManufacturerNormalizer()

    def resolve(self, hint: str | None, evidence: PreAuthEvidence) -> str | None:
        return self.resolve_with_evidence(hint, evidence).selected

    def resolve_with_evidence(
        self, hint: str | None, evidence: PreAuthEvidence
    ) -> ManufacturerResolution:
        detected = self.detect(evidence)
        normalized_hint = self._normalizer.normalize(hint)
        if hint is not None:
            return ManufacturerResolution(
                selected=normalized_hint,
                detected=detected,
                mismatch=(
                    normalized_hint is not None
                    and detected is not None
                    and normalized_hint.casefold() != detected.casefold()
                ),
            )
        return ManufacturerResolution(selected=detected, detected=detected, mismatch=False)

    def detect(self, evidence: PreAuthEvidence) -> str | None:
        for text in self._strings(evidence.capabilities):
            folded = text.casefold()
            for marker, manufacturer in _VENDOR_MARKERS:
                if marker in folded:
                    return manufacturer
        return None

    @classmethod
    def _strings(cls, value: object, depth: int = 0) -> list[str]:
        if depth > 6:
            return []
        if isinstance(value, str):
            return [value[:1024]]
        if isinstance(value, Mapping):
            found: list[str] = []
            for key, item in list(value.items())[:128]:
                found.extend(cls._strings(key, depth + 1))
                found.extend(cls._strings(item, depth + 1))
            return found
        compound_values = getattr(value, "__values__", None)
        if isinstance(compound_values, Mapping):
            return cls._strings(compound_values, depth + 1)
        if isinstance(value, (list, tuple)):
            found = []
            for item in value[:128]:
                found.extend(cls._strings(item, depth + 1))
            return found
        return []
