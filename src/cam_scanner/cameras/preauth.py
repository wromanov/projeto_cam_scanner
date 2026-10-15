"""Bounded, unauthenticated ONVIF discovery and structured manufacturer resolution."""
from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from cam_scanner.cameras.manufacturer import ManufacturerNormalizer
from cam_scanner.cameras.onvif.adapter import _suppress_dependency_logs
from cam_scanner.cameras.transport import ControlledOnvifClient
from cam_scanner.domain.errors import normalize_collection_error
from cam_scanner.domain.models import (
    CameraTarget,
    CollectionAttempt,
    CollectionReport,
    EvidenceRecord,
    is_valid_evidence_value,
)

_STRONG_IDENTITY_KEYS = {"manufacturer", "manufacturername", "manufacturer_name"}
_WEAK_SIGNAL_KEYS = {"server", "realm", "devicename", "device_name", "model", "namespace"}
_KNOWN_FAMILIES = {"Axis", "Hikvision", "Samsung/Hanwha", "Dahua", "Panasonic", "Bosch"}


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
    """Declared hint, observed signals, resolution, and safe routing candidate."""

    selected: str | None
    detected: str | None
    mismatch: bool
    declared: str | None = None
    observed: str | None = None
    resolved: str | None = None
    confidence: str = "UNKNOWN"
    conflicts: tuple[str, ...] = ()
    observed_values: tuple[str, ...] = ()
    weak_values: tuple[str, ...] = ()


class OnvifPreAuthDiscoverer:
    """Use anonymous ONVIF requests and return sanitized per-operation diagnostics."""

    def __init__(
        self,
        client_factory: Callable[..., Any] | None = None,
        timeout_seconds: int = 7,
    ) -> None:
        self._client_factory = client_factory
        self._timeout_seconds = timeout_seconds

    def discover(self, target: CameraTarget, *, context: Any = None) -> PreAuthEvidence:
        """Compatibility API; canonical collection uses discover_with_report."""
        evidence, _ = self.discover_with_report(target, context=context)
        return evidence

    def discover_with_report(
        self, target: CameraTarget, *, context: Any = None
    ) -> tuple[PreAuthEvidence, CollectionReport]:
        _suppress_dependency_logs()
        report = CollectionReport()
        client_factory = self._client_factory
        client_options: dict[str, object] = {
            "host": target.ip,
            "port": 80,
            "timeout": self._timeout_seconds,
        }
        if client_factory is None and context is None:
            return PreAuthEvidence(), CollectionReport().with_attempt(CollectionAttempt(
                stage="CONNECT", operation="create_onvif_client", protocol="ONVIF",
                outcome="FAILED", error_category="INVALID_INPUT",
            ))

        started = time.monotonic()
        try:
            if context is not None:
                context.check("ONVIF")
            client = (ControlledOnvifClient(context, authenticated=False)
                      if client_factory is None else client_factory(**client_options))
            service = client.devicemgmt()
        except KeyboardInterrupt:
            attempt = CollectionAttempt(
                stage="CONNECT",
                operation="create_onvif_client",
                protocol="ONVIF",
                outcome="CANCELLED",
                duration=self._elapsed(started),
            )
            return PreAuthEvidence(), report.with_attempt(attempt)
        except Exception as exception:  # noqa: BLE001 - diagnostics never retain exception text.
            category, http_status, protocol_code = normalize_collection_error(
                exception, stage="CONNECT"
            )
            attempt = CollectionAttempt(
                stage=self._stage_for(category, "CONNECT"),
                operation="create_onvif_client",
                protocol="ONVIF",
                outcome="FAILED",
                duration=self._elapsed(started),
                http_status=http_status,
                protocol_code=protocol_code,
                error_category=category,
            )
            return PreAuthEvidence(), report.with_attempt(attempt)

        values: dict[str, object | None] = {}
        for operation, kwargs in (("GetCapabilities", {"Category": "All"}),):
            method = getattr(service, operation, None)
            if not callable(method):
                report = report.with_attempt(
                    CollectionAttempt(
                        stage="DISCOVERY",
                        operation=operation,
                        protocol="ONVIF",
                        authentication_mechanism="NONE",
                        outcome="SKIPPED",
                        error_category="ENDPOINT_UNSUPPORTED",
                    )
                )
                values[operation] = None
                continue

            started = time.monotonic()
            try:
                if context is not None:
                    context.check("ONVIF")
                value = method(**kwargs)
            except KeyboardInterrupt:
                attempt = CollectionAttempt(
                    stage="DISCOVERY",
                    operation=operation,
                    protocol="ONVIF",
                    authentication_mechanism="NONE",
                    outcome="CANCELLED",
                    duration=self._elapsed(started),
                )
                report = report.with_attempt(attempt)
                return self._finish(values, report, (target.username, target.password))
            except Exception as exception:  # noqa: BLE001 - preserve a typed failure per call.
                category, http_status, protocol_code = normalize_collection_error(
                    exception, stage="DISCOVERY"
                )
                report = report.with_attempt(
                    CollectionAttempt(
                        stage=self._stage_for(category, "DISCOVERY"),
                        operation=operation,
                        protocol="ONVIF",
                        authentication_mechanism="NONE",
                        outcome="FAILED",
                        duration=self._elapsed(started),
                        http_status=http_status,
                        protocol_code=protocol_code,
                        error_category=category,
                    )
                )
                values[operation] = None
                continue

            values[operation] = value if value is not None else None
            report = report.with_attempt(
                CollectionAttempt(
                    stage="DISCOVERY",
                    operation=operation,
                    protocol="ONVIF",
                    authentication_mechanism="NONE",
                    outcome="SUCCESS" if value is not None else "FAILED",
                    duration=self._elapsed(started),
                    error_category=None if value is not None else "INVALID_RESPONSE",
                )
            )
            if value is not None:
                report = report.with_evidence(
                    EvidenceRecord(
                        field="onvif_reachable",
                        value="REACHABLE",
                        source="ONVIF_PREAUTH",
                        confidence="STRONG",
                        protocol="ONVIF",
                        operation=operation,
                    )
                )

        return self._finish(values, report, (target.username, target.password))

    @staticmethod
    def _finish(
        values: Mapping[str, object | None],
        report: CollectionReport,
        sensitive_values: tuple[str, ...] = (),
    ) -> tuple[PreAuthEvidence, CollectionReport]:
        raw_evidence = PreAuthEvidence(
            capabilities=values.get("GetCapabilities"),
            system_date_time=values.get("GetSystemDateAndTime"),
        )
        try:
            resolution = ManufacturerResolver().resolve_with_evidence(
                None, raw_evidence, sensitive_values=sensitive_values
            )
        except Exception as exception:  # noqa: BLE001 - preserve prior reachability evidence.
            category, http_status, protocol_code = normalize_collection_error(
                exception, stage="PARSE"
            )
            return PreAuthEvidence(), report.with_attempt(
                CollectionAttempt(
                    stage="PARSE",
                    operation="resolve_preauth_manufacturer",
                    protocol="ONVIF",
                    outcome="FAILED",
                    http_status=http_status,
                    protocol_code=protocol_code,
                    error_category=category,
                )
            )
        for value in resolution.observed_values:
            report = report.with_evidence(
                EvidenceRecord(
                    field="manufacturer",
                    value=value,
                    source="ONVIF_PREAUTH",
                    confidence="STRONG",
                    protocol="ONVIF",
                    operation="GetCapabilities",
                )
            )
        for value in resolution.weak_values:
            report = report.with_evidence(
                EvidenceRecord(
                    field="manufacturer_signal",
                    value=value,
                    source="ONVIF_PREAUTH",
                    confidence="WEAK",
                    protocol="ONVIF",
                    operation="GetCapabilities",
                )
            )
        # Keep only validated manufacturer signals; never retain raw ONVIF payloads.
        safe_capabilities: dict[str, tuple[str, ...]] = {}
        if resolution.observed_values:
            safe_capabilities["Manufacturer"] = resolution.observed_values
        if resolution.weak_values:
            safe_capabilities["Server"] = resolution.weak_values
        return PreAuthEvidence(capabilities=safe_capabilities), report

    @staticmethod
    def _elapsed(started: float) -> float:
        return max(0.0, float(time.monotonic() - started))

    @staticmethod
    def _stage_for(category: str, default: str) -> str:
        if category in {"CONNECT_TIMEOUT", "CONNECTION_REFUSED", "TLS_ERROR"}:
            return "CONNECT"
        if category in {"AUTH_REJECTED", "AUTHORIZATION_DENIED", "AUTH_MECHANISM_UNSUPPORTED"}:
            return "AUTH"
        if category in {"READ_TIMEOUT", "HTTP_ERROR", "ENDPOINT_UNSUPPORTED"}:
            return "HTTP"
        if category in {"SOAP_FAULT"}:
            return "SOAP"
        if category == "INVALID_RESPONSE":
            return "PARSE"
        return default


class ManufacturerResolver:
    """Resolve only exact structured identity fields and preserve weak/conflicting signals."""

    def __init__(self, normalizer: ManufacturerNormalizer | None = None) -> None:
        self._normalizer = normalizer or ManufacturerNormalizer()

    def resolve(self, hint: str | None, evidence: PreAuthEvidence) -> str | None:
        return self.resolve_with_evidence(hint, evidence).selected

    def resolve_with_evidence(
        self,
        hint: str | None,
        evidence: PreAuthEvidence,
        *,
        sensitive_values: tuple[str, ...] = (),
    ) -> ManufacturerResolution:
        strong_values, weak_values = self._manufacturer_signals(
            evidence.capabilities, sensitive_values=sensitive_values
        )
        declared = self._normalizer.normalize(hint)
        strong_by_fold: dict[str, str] = {}
        for value in strong_values:
            key = value.casefold()
            strong_by_fold[key] = min(
                value,
                strong_by_fold.get(key, value),
                key=lambda item: (item.casefold(), item),
            )
        weak_by_fold: dict[str, str] = {}
        for value in weak_values:
            key = value.casefold()
            weak_by_fold[key] = min(
                value,
                weak_by_fold.get(key, value),
                key=lambda item: (item.casefold(), item),
            )
        strong = tuple(sorted(strong_by_fold.values(), key=lambda item: (item.casefold(), item)))
        weak = tuple(sorted(weak_by_fold.values(), key=lambda item: (item.casefold(), item)))
        conflicts = strong if len({item.casefold() for item in strong}) > 1 else ()
        resolved = strong[0] if len(strong) == 1 else None
        confidence = (
            "CONFLICTING"
            if conflicts
            else "STRONG"
            if resolved is not None
            else "WEAK"
            if weak
            else "UNKNOWN"
        )
        mismatch = (
            resolved is not None
            and declared is not None
            and resolved.casefold() != declared.casefold()
        )
        # A declared hint may guide a registered adapter only when no strong conflict exists.
        selected = None if conflicts else resolved or declared
        observed = resolved or (weak[0] if len(weak) == 1 else None)
        return ManufacturerResolution(
            selected=selected,
            detected=resolved,
            mismatch=mismatch,
            declared=declared,
            observed=observed,
            resolved=resolved,
            confidence=confidence,
            conflicts=conflicts,
            observed_values=strong,
            weak_values=weak,
        )

    def detect(self, evidence: PreAuthEvidence) -> str | None:
        return self.resolve_with_evidence(None, evidence).resolved

    def _manufacturer_signals(
        self,
        value: object,
        depth: int = 0,
        *,
        sensitive_values: tuple[str, ...] = (),
    ) -> tuple[list[str], list[str]]:
        if depth > 8:
            return [], []
        strong: list[str] = []
        weak: list[str] = []
        if isinstance(value, Mapping):
            for key, item in list(value.items())[:128]:
                normalized_key = str(key).replace("-", "_").casefold()
                if normalized_key in _STRONG_IDENTITY_KEYS:
                    for text in self._text_values(item):
                        if len(text) > 256 or not is_valid_evidence_value(
                            "manufacturer", text, sensitive_values=sensitive_values
                        ):
                            continue
                        normalized = self._normalizer.normalize(text)
                        if normalized:
                            strong.append(normalized)
                    continue
                if normalized_key in _WEAK_SIGNAL_KEYS and isinstance(item, str):
                    normalized = (
                        self._known_family_alias(item)
                        if is_valid_evidence_value(
                            "manufacturer_signal", item, sensitive_values=sensitive_values
                        )
                        else None
                    )
                    if normalized:
                        weak.append(normalized)
                    continue
                child_strong, child_weak = self._manufacturer_signals(
                    item, depth + 1, sensitive_values=sensitive_values
                )
                strong.extend(child_strong)
                weak.extend(child_weak)
        elif isinstance(value, (list, tuple)):
            for item in value[:128]:
                child_strong, child_weak = self._manufacturer_signals(
                    item, depth + 1, sensitive_values=sensitive_values
                )
                strong.extend(child_strong)
                weak.extend(child_weak)
        else:
            compound_values = getattr(value, "__values__", None)
            if isinstance(compound_values, Mapping):
                return self._manufacturer_signals(
                    compound_values, depth + 1, sensitive_values=sensitive_values
                )
        return strong, weak

    @staticmethod
    def _text_values(value: object, depth: int = 0) -> list[str]:
        if depth > 4:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, (list, tuple)):
            result: list[str] = []
            for item in value[:32]:
                result.extend(ManufacturerResolver._text_values(item, depth + 1))
            return result
        compound_values = getattr(value, "__values__", None)
        if isinstance(compound_values, Mapping):
            for name, item in compound_values.items():
                if str(name).replace("-", "_").casefold() in _STRONG_IDENTITY_KEYS:
                    return ManufacturerResolver._text_values(item, depth + 1)
        return []

    def _known_family_alias(self, value: str) -> str | None:
        normalized = self._normalizer.normalize(value)
        if normalized is None:
            return None
        return next(
            (family for family in _KNOWN_FAMILIES if family.casefold() == normalized.casefold()),
            None,
        )
