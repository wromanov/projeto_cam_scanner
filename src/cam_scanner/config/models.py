"""Immutable, strictly validated effective configuration."""
from __future__ import annotations

import ipaddress
import math
from dataclasses import dataclass, field

DEFAULT_MAX_WORKERS = 8
MIN_WORKERS = 1
MAX_WORKERS = 32
MAX_RETRIES = 1
RTSP_CONCURRENCY = 1
THUMBNAIL_WIDTH = 320
THUMBNAIL_HEIGHT = 180
JPEG_QUALITY = 75
_TRANSPORT_COMPONENTS = frozenset(
    {
        "onvif_device", "onvif_media", "snapshot_onvif", "snapshot_vendor",
        "vendor_axis", "vendor_dahua", "vendor_hanwha", "vendor_panasonic",
        "vendor_hikvision", "rtsp",
    }
)
_TRANSPORT_PROTOCOLS = frozenset({"https", "http", "rtsp", "rtsps"})
_PROFILE_COMPONENTS = frozenset({
    "vendor_axis", "vendor_hikvision", "vendor_dahua", "vendor_hanwha",
    "vendor_panasonic",
})
@dataclass(frozen=True, slots=True)
class TransportRule:
    """One exact destination authorization; wildcards and networks are invalid."""

    target: str
    component: str
    protocol: str
    host: str | None
    port: int

    def __post_init__(self) -> None:
        if not isinstance(self.target, str):
            raise TypeError("Regra de transporte inválida.")
        try:
            parsed_target = ipaddress.ip_address(self.target)
        except ValueError:
            raise ValueError("target deve ser um endereço IP exato.") from None
        if parsed_target.compressed != self.target:
            raise ValueError("target deve usar a representação canônica do IP.")
        if type(self.component) is not str or self.component not in _TRANSPORT_COMPONENTS:
            raise ValueError("Componente de transporte inválido.")
        if type(self.protocol) is not str or self.protocol not in _TRANSPORT_PROTOCOLS:
            raise ValueError("Protocolo de transporte inválido.")
        expected_protocol = "rtsp" if self.component == "rtsp" else None
        if expected_protocol and self.protocol not in {"rtsp", "rtsps"}:
            raise ValueError("Protocolo incompatível com o componente.")
        if not expected_protocol and self.protocol not in {"http", "https"}:
            raise ValueError("Protocolo incompatível com o componente.")
        if type(self.port) is not int or not 1 <= self.port <= 65535:
            raise ValueError("Porta de transporte inválida.")
        if self.host is not None:
            if (not isinstance(self.host, str) or not self.host or len(self.host) > 253
                    or self.host != self.host.strip() or "*" in self.host
                    or self.host.endswith(".")):
                raise ValueError("host deve ser um endereço IP exato.")
            try:
                parsed_host = ipaddress.ip_address(self.host)
            except ValueError:
                raise ValueError("host deve ser um endereço IP exato.") from None
            if parsed_host.compressed != self.host:
                raise ValueError("host deve usar a representação canônica do IP.")


@dataclass(frozen=True, slots=True)
class TransportProfile:
    """Closed, offline declaration for one exact-target HTTP exception."""

    id: str
    targets: tuple[str, ...]
    component: str
    protocol: str
    port: int
    auth_mode: str
    authorization_ref: str
    http_risk_accepted: bool

    def __post_init__(self) -> None:
        if not _valid_transport_id(self.id) or not _valid_transport_id(self.authorization_ref):
            raise ValueError("Identificador de perfil inválido.")
        if self.id in {"HTTPS_DEFAULT", "LEGACY_EXACT"}:
            raise ValueError("ID de perfil reservado.")
        if (not isinstance(self.targets, tuple) or not self.targets
                or any(type(target) is not str for target in self.targets)):
            raise ValueError("Targets do perfil inválidos.")
        parsed_targets: list[str] = []
        for target in self.targets:
            try:
                address = ipaddress.ip_address(target)
            except ValueError:
                raise ValueError("Target de perfil deve ser um IP exato.") from None
            if address.compressed != target:
                raise ValueError("Target de perfil deve ser canônico.")
            parsed_targets.append(target)
        if len(set(parsed_targets)) != len(parsed_targets):
            raise ValueError("Targets de perfil duplicados.")
        if self.component not in _PROFILE_COMPONENTS or self.protocol != "http":
            raise ValueError("Componente ou protocolo de perfil inválido.")
        if type(self.port) is not int or not 1 <= self.port <= 65535:
            raise ValueError("Porta de perfil inválida.")
        expected_auth = (
            "PUBLIC_NONE" if self.component == "vendor_axis"
            else "NATIVE_DIGEST_EXISTING"
        )
        if self.auth_mode != expected_auth:
            raise ValueError("Modo de autenticação incompatível com o componente.")
        if self.http_risk_accepted is not True:
            raise ValueError("Perfil HTTP exige aceite explícito de risco.")


@dataclass(frozen=True, slots=True)
class TransportPolicyMetadata:
    """Sanitized, closed provenance attached to a compiled transport choice."""

    policy_id: str
    authorization_ref: str | None
    auth_mode: str
    scheme: str

    def __post_init__(self) -> None:
        if (not _valid_transport_id(self.policy_id)
                or (self.authorization_ref is not None
                    and not _valid_transport_id(self.authorization_ref))
                or self.auth_mode not in {
                    "NONE", "EXISTING", "PUBLIC_NONE", "NATIVE_DIGEST_EXISTING",
                }
                or self.scheme not in {"http", "https"}):
            raise ValueError("Metadados de transporte inválidos.")


@dataclass(frozen=True, slots=True)
class PlannedTransport:
    target: str
    component: str
    rule: TransportRule | None
    metadata: TransportPolicyMetadata

    def __post_init__(self) -> None:
        if (type(self.target) is not str or not _valid_ip(self.target)
                or self.component not in _TRANSPORT_COMPONENTS
                or (self.rule is not None and (
                    self.rule.target != self.target or self.rule.component != self.component
                    or self.rule.protocol != self.metadata.scheme
                ))):
            raise ValueError("Entrada de plano de transporte inválida.")


@dataclass(frozen=True, slots=True)
class TransportExecutionPlan:
    """Immutable per-run plan compiled before any network-capable object exists."""

    selection_id: str
    entries: tuple[PlannedTransport, ...]
    rules: tuple[TransportRule, ...]

    def __post_init__(self) -> None:
        if (not _valid_transport_id(self.selection_id)
                or not isinstance(self.entries, tuple)
                or any(not isinstance(entry, PlannedTransport) for entry in self.entries)
                or not isinstance(self.rules, tuple)
                or any(not isinstance(rule, TransportRule) for rule in self.rules)):
            raise ValueError("Plano de transporte inválido.")
        if len({(entry.target, entry.component) for entry in self.entries}) != len(self.entries):
            raise ValueError("Plano de transporte duplicado.")
        entries = {(entry.target, entry.component): entry for entry in self.entries}
        if any(entries.get((rule.target, rule.component)) is None
               or entries[(rule.target, rule.component)].rule != rule
               for rule in self.rules):
            raise ValueError("Regras fora do plano de transporte.")

    def for_target(self, target: str, component: str) -> PlannedTransport | None:
        return next((entry for entry in self.entries
                     if entry.target == target and entry.component == component), None)


def _valid_transport_id(value: object) -> bool:
    if (type(value) is not str or not 1 <= len(value) <= 64
            or not all(char.isascii() and (char.isalnum() or char in "_-")
                       for char in value)):
        return False
    lowered = value.casefold()
    return not any(marker in lowered for marker in (
        "password", "passwd", "secret", "token", "credential", "username",
    ))


def _valid_ip(value: str) -> bool:
    try:
        parsed = ipaddress.ip_address(value)
    except ValueError:
        return False
    return parsed.compressed == value


@dataclass(frozen=True, slots=True)
class EffectiveConfig:
    """Validated values delivered to runtime consumers."""

    connect_timeout_seconds: float = 3.0
    request_timeout_seconds: float = 7.0
    onvif_budget_seconds: float = 15.0
    manufacturer_budget_seconds: float = 10.0
    camera_soft_deadline_seconds: float = 45.0
    default_max_workers: int = DEFAULT_MAX_WORKERS
    max_workers: int = DEFAULT_MAX_WORKERS
    max_retries: int = 0
    retry_backoff_seconds: int = field(default=1, init=False)
    snapshot_http_timeout_seconds: float = 10.0
    rtsp_open_timeout_seconds: float = 8.0
    rtsp_first_frame_timeout_seconds: float = 5.0
    keep_temporary_files: bool = field(default=False, init=False)
    max_concurrent_rtsp: int = field(default=RTSP_CONCURRENCY, init=False)
    thumbnail_width: int = field(default=THUMBNAIL_WIDTH, init=False)
    thumbnail_height: int = field(default=THUMBNAIL_HEIGHT, init=False)
    jpeg_quality: int = field(default=JPEG_QUALITY, init=False)
    log_level: str = "INFO"
    log_retention_days: int = 30
    log_max_file_size_mb: int = 10
    transport_rules: tuple[TransportRule, ...] = ()
    transport_profiles: tuple[TransportProfile, ...] = ()
    transport_plan: TransportExecutionPlan | None = None

    def __post_init__(self) -> None:
        ranges = {
            "connect_timeout_seconds": (0.0, 3.0),
            "request_timeout_seconds": (0.0, 7.0),
            "onvif_budget_seconds": (0.0, 15.0),
            "manufacturer_budget_seconds": (0.0, 10.0),
            "camera_soft_deadline_seconds": (0.0, 45.0),
            "snapshot_http_timeout_seconds": (0.0, 10.0),
            "rtsp_open_timeout_seconds": (0.0, 8.0),
            "rtsp_first_frame_timeout_seconds": (0.0, 5.0),
        }
        for name, (lower, upper) in ranges.items():
            value = getattr(self, name)
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or not lower < value <= upper):
                raise ValueError(f"{name} fora do limite aprovado.")
        for value in (self.default_max_workers, self.max_workers):
            if type(value) is not int or not MIN_WORKERS <= value <= MAX_WORKERS:
                raise ValueError("max_workers deve ser um inteiro entre 1 e 32.")
        if type(self.max_retries) is not int or not 0 <= self.max_retries <= MAX_RETRIES:
            raise ValueError("max_retries deve ser 0 ou 1.")
        if type(self.log_retention_days) is not int or not 1 <= self.log_retention_days <= 30:
            raise ValueError("retention_days deve estar entre 1 e 30.")
        if type(self.log_max_file_size_mb) is not int or not 1 <= self.log_max_file_size_mb <= 10:
            raise ValueError("max_file_size_mb deve estar entre 1 e 10.")
        if self.log_level not in {"INFO", "DEBUG"}:
            raise ValueError("level deve ser INFO ou DEBUG.")
        if (not isinstance(self.transport_rules, tuple)
                or any(not isinstance(rule, TransportRule) for rule in self.transport_rules)):
            raise ValueError("transport_rules deve ser uma tupla imutável de regras.")
        if len(set(self.transport_rules)) != len(self.transport_rules):
            raise ValueError("Regras de transporte duplicadas.")
        rule_by_scope: dict[tuple[str, str], TransportRule] = {}
        for rule in self.transport_rules:
            scope = (rule.target, rule.component)
            previous = rule_by_scope.setdefault(scope, rule)
            if previous != rule:
                raise ValueError("Regras de transporte conflitantes.")
        if (not isinstance(self.transport_profiles, tuple)
                or any(not isinstance(profile, TransportProfile)
                       for profile in self.transport_profiles)):
            raise ValueError("transport_profiles deve ser uma tupla imutável.")
        if len({profile.id for profile in self.transport_profiles}) != len(self.transport_profiles):
            raise ValueError("IDs de perfil de transporte duplicados.")
        for left_index, left in enumerate(self.transport_profiles):
            for right in self.transport_profiles[left_index + 1:]:
                if (left.component == right.component
                        and set(left.targets).intersection(right.targets)):
                    raise ValueError("Perfis de transporte conflitantes.")
            if any(rule.target in left.targets and rule.component == left.component
                   for rule in self.transport_rules):
                raise ValueError("Perfil conflita com regra de transporte.")
        if self.transport_plan is not None and not isinstance(
            self.transport_plan, TransportExecutionPlan
        ):
            raise ValueError("transport_plan inválido.")
