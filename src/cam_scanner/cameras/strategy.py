"""Vendor-first collection routing with anonymous discovery and generic ONVIF fallback."""
from __future__ import annotations

import logging
from dataclasses import replace

from cam_scanner.cameras.collector import CameraCollector
from cam_scanner.cameras.manufacturer import ManufacturerNormalizer
from cam_scanner.cameras.onvif.adapter import GenericOnvifCollector
from cam_scanner.cameras.preauth import (
    ManufacturerResolver,
    OnvifPreAuthDiscoverer,
    PreAuthEvidence,
)
from cam_scanner.cameras.registry import AdapterRegistry
from cam_scanner.domain.enums import CollectionMethod, CollectionStatus, ErrorCode
from cam_scanner.domain.models import CameraResult, CameraTarget


class VendorFirstCollector(CameraCollector):
    """Select one known vendor adapter before falling back to generic ONVIF."""

    def __init__(
        self,
        onvif_collector: CameraCollector | None = None,
        registry: AdapterRegistry | None = None,
        discoverer: OnvifPreAuthDiscoverer | None = None,
        resolver: ManufacturerResolver | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._onvif = onvif_collector or GenericOnvifCollector()
        self._registry = registry or AdapterRegistry()
        self._discoverer = discoverer or OnvifPreAuthDiscoverer()
        self._resolver = resolver or ManufacturerResolver()
        self._normalizer = ManufacturerNormalizer()
        self._logger = logger or logging.getLogger("cam_scanner")

    def collect(self, target: CameraTarget) -> CameraResult:
        try:
            evidence = self._discoverer.discover(target)
        except Exception:  # noqa: BLE001 - discovery failure does not prevent generic fallback.
            evidence = None
        if evidence is None:
            evidence = PreAuthEvidence()
        manufacturer = self._resolver.resolve(None, evidence)
        adapter = self._registry.get(manufacturer) if manufacturer is not None else None

        if adapter is not None:
            try:
                result = adapter.collect(target)
            except Exception:  # noqa: BLE001 - one selected adapter may fall back to generic ONVIF.
                self._logger.warning("Registered vendor adapter failed; using generic ONVIF fallback")
            else:
                if isinstance(result, CameraResult) and result.status is not CollectionStatus.FAILED:
                    if not self._needs_onvif_complement(result):
                        return self._merge_manufacturer(result, manufacturer)
                    try:
                        complement = self._onvif.collect(target)
                    except Exception:  # noqa: BLE001 - successful vendor evidence remains usable.
                        return self._merge_manufacturer(result, manufacturer)
                    return self._merge_results(result, complement, manufacturer)

        try:
            result = self._onvif.collect(target)
        except Exception as exception:
            if not evidence.has_evidence:
                raise
            code = self._auth_error_code(exception)
            if code is None:
                raise
            return CameraResult(
                ip=target.ip,
                status=CollectionStatus.PARTIAL_SUCCESS,
                manufacturer=manufacturer,
                error_code=ErrorCode.AUTH_ERROR,
                error_message="A câmera forneceu evidência pré-autenticação, mas recusou autenticação ONVIF.",
                collection_method=CollectionMethod.ONVIF,
            )
        self._report_manufacturer_mismatch(manufacturer, result.manufacturer)
        return self._merge_manufacturer(result, manufacturer)

    @staticmethod
    def _needs_onvif_complement(result: CameraResult) -> bool:
        return any(
            getattr(result, field) is None
            for field in ("manufacturer", "model", "serial", "firmware")
        )

    def _merge_results(
        self,
        vendor_result: CameraResult,
        onvif_result: CameraResult,
        manufacturer: str | None,
    ) -> CameraResult:
        self._report_manufacturer_mismatch(manufacturer, onvif_result.manufacturer)
        values: dict[str, object] = {}
        for field in (
            "hostname",
            "manufacturer",
            "manufacturer_original",
            "model",
            "serial",
            "firmware",
            "hardware_id",
            "mac",
        ):
            vendor_value = getattr(vendor_result, field)
            onvif_value = getattr(onvif_result, field)
            if vendor_value is None and onvif_value is not None:
                values[field] = onvif_value
        merged = replace(vendor_result, **values)
        return self._merge_manufacturer(merged, manufacturer)

    def _report_manufacturer_mismatch(
        self, resolved_manufacturer: str | None, reported_manufacturer: str | None
    ) -> None:
        resolved = self._normalizer.normalize(resolved_manufacturer)
        reported = self._normalizer.normalize(reported_manufacturer)
        if resolved is not None and reported is not None and resolved.casefold() != reported.casefold():
            self._logger.warning("Manufacturer evidence mismatch detected; preserving existing fields")

    def _merge_manufacturer(self, result: CameraResult, manufacturer: str | None) -> CameraResult:
        if manufacturer is None or result.manufacturer is not None:
            return result
        return replace(result, manufacturer=manufacturer)

    @staticmethod
    def _auth_error_code(exception: Exception) -> ErrorCode | None:
        current: BaseException | None = exception
        seen: set[int] = set()
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            response = getattr(current, "response", None)
            if getattr(response, "status_code", None) in {401, 403}:
                return ErrorCode.AUTH_ERROR
            text = str(current).casefold().replace("_", "")
            if any(
                marker in text
                for marker in (
                    "notauthorized",
                    "not authorized",
                    "unauthorized",
                    "authentication failed",
                    "invalid credentials",
                    "bad credentials",
                )
            ):
                return ErrorCode.AUTH_ERROR
            if type(current).__name__ == "Fault" and "auth" in text:
                return ErrorCode.AUTH_ERROR
            original = getattr(current, "original_exception", None)
            current = (
                original
                if isinstance(original, BaseException)
                else current.__cause__ or current.__context__
            )
        return None
