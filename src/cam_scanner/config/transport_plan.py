"""Offline compilation of immutable, per-run transport selections."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import replace

from cam_scanner.config.models import (
    EffectiveConfig,
    PlannedTransport,
    TransportExecutionPlan,
    TransportPolicyMetadata,
    TransportRule,
)
from cam_scanner.domain.errors import ConfigurationError

_VENDOR_COMPONENTS = frozenset({
    "vendor_axis", "vendor_hikvision", "vendor_dahua", "vendor_hanwha",
    "vendor_panasonic",
})


def compile_transport_plan(
    config: EffectiveConfig,
    input_targets: Iterable[object],
    known_components: Mapping[str, str],
    selection_id: str = "HTTPS_DEFAULT",
) -> TransportExecutionPlan:
    """Compile a frozen plan from already validated input rows; never performs I/O.

    ``known_components`` must contain only vendor components resolved by the caller
    before network access. It is deliberately not inferred from profile data.
    Duplicate input rows collapse to one immutable rule while callers retain their
    own row/session/credential state.
    """
    if not isinstance(config, EffectiveConfig):
        raise ConfigurationError("Configuração de transporte inválida.")
    targets: list[str] = []
    for row in input_targets:
        target = row if isinstance(row, str) else getattr(row, "ip", None)
        if type(target) is not str or not _canonical_ip(target):
            raise ConfigurationError("A entrada contém target inválido.")
        if target not in targets:
            targets.append(target)
    if not targets:
        raise ConfigurationError("A seleção exige targets de entrada.")
    if not isinstance(known_components, Mapping):
        raise ConfigurationError("Componentes conhecidos inválidos.")
    components = dict(known_components)
    if any(target not in targets or component not in _VENDOR_COMPONENTS
           for target, component in components.items()):
        raise ConfigurationError("Componente não elegível para seleção de transporte.")

    rules: list[TransportRule] = [
        rule for rule in config.transport_rules
        if rule.protocol == "https" and rule.target in targets
    ]
    entries: list[PlannedTransport] = [
        PlannedTransport(
            rule.target, rule.component, rule,
            TransportPolicyMetadata("HTTPS_DEFAULT", None, "NONE", "https"),
        )
        for rule in rules
    ]
    for target in targets:
        component = components.get(target)
        if component and not any(entry.target == target and entry.component == component
                                 for entry in entries):
            entries.append(PlannedTransport(
                target, component, None,
                TransportPolicyMetadata("HTTPS_DEFAULT", None, "NONE", "https"),
            ))

    if selection_id == "HTTPS_DEFAULT":
        return TransportExecutionPlan(selection_id, tuple(entries), tuple(rules))

    if selection_id == "LEGACY_EXACT":
        legacy_http = [rule for rule in config.transport_rules
                       if rule.protocol == "http" and rule.target in targets
                       and rule.component in _VENDOR_COMPONENTS]
        if not legacy_http:
            raise ConfigurationError("Não há regra HTTP legada elegível no lote.")
        _reject_rule_conflicts(config.transport_rules)
        for rule in legacy_http:
            rules.append(rule)
            entries = [entry for entry in entries
                       if (entry.target, entry.component) != (rule.target, rule.component)]
            entries.append(PlannedTransport(
                rule.target, rule.component, rule,
                TransportPolicyMetadata("LEGACY_EXACT", None, "EXISTING", "http"),
            ))
        return TransportExecutionPlan(selection_id, tuple(entries), tuple(rules))

    profile = next((item for item in config.transport_profiles
                    if item.id == selection_id), None)
    if profile is None:
        raise ConfigurationError("Seleção de transporte desconhecida.")
    eligible = [target for target in targets if target in profile.targets
                and components.get(target) == profile.component]
    if not eligible:
        raise ConfigurationError("Perfil sem interseção elegível com as entradas.")
    if any(rule.target in eligible and rule.component == profile.component
           for rule in config.transport_rules):
        raise ConfigurationError("Perfil conflita com regra legada de transporte.")
    for target in eligible:
        rule = TransportRule(target, profile.component, "http", None, profile.port)
        rules.append(rule)
        entries = [entry for entry in entries
                   if (entry.target, entry.component) != (target, profile.component)]
        entries.append(PlannedTransport(
            target, profile.component, rule,
            TransportPolicyMetadata(profile.id, profile.authorization_ref,
                                     profile.auth_mode, "http"),
        ))
    return TransportExecutionPlan(selection_id, tuple(entries), tuple(rules))


def select_transport(
    config: EffectiveConfig,
    input_targets: Iterable[object],
    known_components: Mapping[str, str],
    selection_id: str = "HTTPS_DEFAULT",
) -> EffectiveConfig:
    """Return a new effective config with a frozen plan bound for one execution."""
    plan = compile_transport_plan(config, input_targets, known_components, selection_id)
    return replace(config, transport_plan=plan)


def _reject_rule_conflicts(rules: tuple[TransportRule, ...]) -> None:
    by_key: dict[tuple[str, str], TransportRule] = {}
    for rule in rules:
        key = (rule.target, rule.component)
        previous = by_key.setdefault(key, rule)
        if previous != rule:
            raise ConfigurationError("Regras legadas de transporte conflitantes.")


def _canonical_ip(value: str) -> bool:
    import ipaddress

    try:
        parsed = ipaddress.ip_address(value)
    except ValueError:
        return False
    return parsed.compressed == value
