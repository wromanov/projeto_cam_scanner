from __future__ import annotations

import json
from dataclasses import fields

import pytest

from cam_scanner.application.collection_context import CollectionContext, CollectionTLSFailure
from cam_scanner.application.inventory_service import (
    InventoryService,
    TransportInputDescriptor,
    TransportSelectionOption,
)
from cam_scanner.cameras.manufacturers.axis import AxisAdapter
from cam_scanner.cameras.manufacturers.panasonic import PanasonicAdapter
from cam_scanner.cameras.preauth import ManufacturerResolver, PreAuthEvidence
from cam_scanner.cameras.transport import TargetRejected, TargetTransportPolicy
from cam_scanner.config.loader import ConfigurationError, load_settings
from cam_scanner.config.models import EffectiveConfig, TransportRule
from cam_scanner.config.transport_plan import select_transport
from cam_scanner.domain.models import (
    CameraResult,
    CameraTarget,
    CollectionAttempt,
    ModelHint,
    parse_model_hint,
)
from cam_scanner.excel.reader import ExcelInputError, ExcelReader
from cam_scanner.terminal.ui import TerminalUI


class _Response:
    def __init__(self, status: int, body: bytes, headers: dict[str, str] | None = None) -> None:
        self.status_code = status
        self.headers = {"content-length": str(len(body)), **(headers or {})}
        self._body = body
        self.closed = False

    def iter_content(self, chunk_size: int):
        yield self._body

    def close(self) -> None:
        self.closed = True


class _Cookies:
    def clear(self) -> None:
        pass


class _Session:
    def __init__(self, *responses: _Response) -> None:
        self.responses = list(responses)
        self.requests: list[tuple[str, str, dict]] = []
        self.cookies = _Cookies()
        self.trust_env = True
        self.proxies = {}

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def post(self, url: str, **kwargs):
        self.requests.append(("POST", url, kwargs))
        return self.responses.pop(0)

    def get(self, url: str, **kwargs):
        self.requests.append(("GET", url, kwargs))
        return self.responses.pop(0)


def _target() -> CameraTarget:
    return CameraTarget("192.0.2.10", "synthetic-user", "synthetic-password")


def _json(payload: dict) -> bytes:
    return json.dumps(payload).encode("utf-8")


def test_model_hint_nfc_ascii_spaces_and_casefold() -> None:
    hint = parse_model_hint("  Cafe\u0301   S2531L  ")

    assert hint == ModelHint("  Cafe\u0301   S2531L  ")
    assert hint.declared == "  Cafe\u0301   S2531L  "
    assert hint.normalized == "Café S2531L"
    assert hint.match_key == "café s2531l"


@pytest.mark.parametrize("value", ["x" * 256, "A" * 256])
def test_model_hint_accepts_256_codepoints(value: str) -> None:
    assert parse_model_hint(value) is not None


@pytest.mark.parametrize(
    "value",
    [
        "x" * 257,
        "camera\x00model",
        "camera\x1b[31m",
        "camera\x85model",
        "camera\ud800model",
        "https://192.0.2.10/model",
        "user=sensitive-user",
        "=HYPERLINK(\"https://invalid.example\")",
        "+SUM(1,1)",
        "@SUM(1,1)",
        "   ",
        123,
    ],
)
def test_model_hint_discards_controls_secrets_urls_formula_like_and_invalid_values(value) -> None:
    assert parse_model_hint(value, sensitive_values=("sensitive-user",)) is None


def test_model_hint_secret_rejection_does_not_retain_or_repr_secret() -> None:
    secret = "synthetic-password"

    hint = parse_model_hint(f"WV-{secret}-S2531L", sensitive_values=(secret,))

    assert hint is None
    assert secret not in repr(ModelHint("WV-S2531L"))


def test_model_hint_is_not_a_vendor_routing_signal() -> None:
    resolver = ManufacturerResolver()

    resolution = resolver.resolve_with_evidence(
        ModelHint("WV-S2531L"), PreAuthEvidence()
    )

    assert resolution.selected is None


def test_excel_model_column_is_optional_case_insensitive_and_position_independent(tmp_path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    path = tmp_path / "optional-model.xlsx"
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(("NOTES", "password", "Ip", "MoDeLo", "username"))
    sheet.append(("extra", "synthetic-password", "192.0.2.10", " WV-S2531L ", "synthetic-user"))
    workbook.save(path)
    workbook.close()

    row = next(ExcelReader().read(path).rows)

    assert row.valid
    assert row.model_hint is not None
    assert row.model_hint.normalized == "WV-S2531L"
    assert row.model_hint_invalid is False
    assert "synthetic-password" not in repr(row)


def test_excel_model_column_may_be_absent_and_blank(tmp_path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    for headers, row_values in (
        (("IP", "USERNAME", "PASSWORD"), ("192.0.2.10", "u", "p")),
        (("IP", "USERNAME", "PASSWORD", "MODELO"), ("192.0.2.10", "u", "p", "   ")),
    ):
        path = tmp_path / f"optional-{len(headers)}-{len(row_values)}.xlsx"
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(headers)
        sheet.append(row_values)
        workbook.save(path)
        workbook.close()
        parsed = next(ExcelReader().read(path).rows)
        assert parsed.valid
        assert parsed.model_hint is None


def test_excel_duplicate_model_header_fails_before_rows_are_iterated(tmp_path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    path = tmp_path / "duplicate-model.xlsx"
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(("IP", "USERNAME", "PASSWORD", "MODELO", " modelo "))
    sheet.append(("192.0.2.10", "u", "p", "A", "B"))
    workbook.save(path)
    workbook.close()

    with pytest.raises(ExcelInputError, match="MODELO"):
        ExcelReader().read(path)


def test_excel_formula_cell_is_never_evaluated_as_model_hint(tmp_path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    path = tmp_path / "formula-model.xlsx"
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(("IP", "USERNAME", "PASSWORD", "MODELO"))
    sheet.append(("192.0.2.10", "u", "p", '=HYPERLINK("https://invalid.example")'))
    workbook.save(path)
    workbook.close()

    parsed = next(ExcelReader().read(path).rows)

    assert parsed.valid
    assert parsed.model_hint is None
    assert parsed.model_hint_invalid is False


def test_axis_public_profile_never_uses_credentials_or_replays_401() -> None:
    session = _Session(_Response(401, b""))

    report = AxisAdapter(session_factory=lambda: session).collect_report(_target())

    assert report.attempts[0].authentication_mechanism == "NONE"
    assert len(session.requests) == 1
    _, _, options = session.requests[0]
    assert "auth" not in options
    assert "cookies" not in options
    assert options["verify"] is True


def test_panasonic_profile_matches_only_exact_documented_model() -> None:
    not_exact = _Session()
    exact = _Session(_Response(200, b"NAME=WV-S2531L\nSERIAL=ABC123\nVERSION=2.50\n"))

    skipped = PanasonicAdapter(
        session_factory=lambda: not_exact,
        profile="i-pro-command-interface-v1.17:WV-S2531",
    ).collect_report(_target())
    collected = PanasonicAdapter(
        session_factory=lambda: exact,
        profile="i-pro-command-interface-v1.17:WV-S2531L",
    ).collect_report(_target())

    assert skipped.attempts[0].outcome == "SKIPPED"
    assert not not_exact.requests
    assert collected.value_for("model") == "WV-S2531L"
    assert collected.value_for("manufacturer") is None
    assert len(exact.requests) == 1


def test_collection_metadata_is_allowlisted_and_secret_free() -> None:
    attempt = CollectionAttempt(
        stage="HTTP",
        operation="select_transport_policy",
        outcome="SUCCESS",
        metadata={
            "policy_id": "legacy-exact",
            "authorization_ref": "AUTH-2026-01",
            "scheme": "HTTP",
            "auth_mode": "NATIVE_DIGEST_EXISTING",
            "model_hint_match": True,
            "username": "synthetic-user",
            "authorization": "Bearer synthetic-password",
            "unknown": "untrusted-value",
        },
    )

    assert dict(attempt.metadata) == {
        "policy_id": "legacy-exact",
        "authorization_ref": "AUTH-2026-01",
        "scheme": "HTTP",
        "auth_mode": "NATIVE_DIGEST_EXISTING",
        "model_hint_match": True,
    }
    assert "synthetic-user" not in repr(attempt)
    assert "synthetic-password" not in repr(attempt)


def test_camera_result_stays_at_exactly_fourteen_fields() -> None:
    assert {item.name for item in fields(CameraResult)} == {
        "ip", "status", "hostname", "manufacturer", "manufacturer_original",
        "model", "serial", "firmware", "hardware_id", "mac", "error_code",
        "error_message", "collection_method", "duration",
    }


@pytest.mark.parametrize(
    "url",
    [
        "http://192.0.2.10:80/cgi-bin/param.cgi",
        "https://192.0.2.11:443/onvif/device_service",
        "https://synthetic-user:synthetic-password@192.0.2.10/endpoint",
    ],
)
def test_transport_rejects_unapproved_http_cross_target_and_url_credentials(url: str) -> None:
    context = CollectionContext(_target(), EffectiveConfig())
    policy = TargetTransportPolicy(context, session_factory=lambda: pytest.fail("unexpected session"))

    with pytest.raises(TargetRejected):
        policy.authorize("vendor_panasonic", url)


def test_transport_accepts_only_exact_legacy_http_rule() -> None:
    rule = TransportRule("192.0.2.10", "vendor_panasonic", "http", None, 8080)
    config = EffectiveConfig(transport_rules=(rule,))
    selected = select_transport(
        config, ["192.0.2.10"], {"192.0.2.10": "vendor_panasonic"}, "LEGACY_EXACT"
    )
    context = CollectionContext(_target(), selected)
    policy = TargetTransportPolicy(context, session_factory=lambda: pytest.fail("unexpected session"))

    assert policy.authorize(
        "vendor_panasonic", "http://192.0.2.10:8080/cgi-bin/param.cgi"
    ).startswith("http://192.0.2.10:8080/")
    with pytest.raises(TargetRejected):
        policy.authorize("vendor_axis", "http://192.0.2.10:8080/axis-cgi/basicdeviceinfo.cgi")


def test_tls_failure_closes_transport_before_creating_session() -> None:
    context = CollectionContext(_target(), EffectiveConfig())
    created: list[object] = []
    policy = TargetTransportPolicy(context, session_factory=lambda: created.append(object()))
    context.mark_tls_failure()

    with pytest.raises(CollectionTLSFailure):
        policy.request(
            "vendor_panasonic", "GET", "https://192.0.2.10/cgi-bin/param.cgi",
            source="NATIVE", authenticated=False,
        )

    assert created == []


def test_transport_profile_schema_is_closed_and_preselectable_before_io(tmp_path) -> None:
    """Contract test: selected immutable plans must compile before any I/O is possible."""
    path = tmp_path / "profiles.toml"
    path.write_text(
        """\
[transport]

[[transport.profiles]]
id = "field-a"
targets = ["192.0.2.10"]
component = "vendor_panasonic"
protocol = "http"
port = 8080
auth_mode = "NATIVE_DIGEST_EXISTING"
authorization_ref = "AUTH-2026-01"
http_risk_accepted = true
""",
        encoding="utf-8",
    )

    effective = load_settings(path)
    selected = select_transport(
        effective, ["192.0.2.10"], {"192.0.2.10": "vendor_panasonic"}, "field-a"
    )

    assert effective.transport_profiles[0].targets == ("192.0.2.10",)
    assert effective.transport_profiles[0].http_risk_accepted is True
    assert selected.transport_plan.selection_id == "field-a"
    assert selected.transport_plan.rules == (
        TransportRule("192.0.2.10", "vendor_panasonic", "http", None, 8080),
    )
    assert selected.transport_plan.for_target(
        "192.0.2.10", "vendor_panasonic"
    ).metadata.authorization_ref == "AUTH-2026-01"
    transport = TargetTransportPolicy(
        CollectionContext(_target(), selected),
        session_factory=lambda: pytest.fail("plan inspection must not create a session"),
    )
    assert transport.policy_metadata(
        "vendor_panasonic", "http://192.0.2.10:8080/cgi-bin/param.cgi"
    ) == {
        "policy_id": "field-a",
        "authorization_ref": "AUTH-2026-01",
        "auth_mode": "NATIVE_DIGEST_EXISTING",
        "scheme": "http",
    }


@pytest.mark.parametrize(
    "field_value",
    [
        'targets = ["192.0.2.0/24"]',
        'targets = ["camera.example"]',
        'component = "onvif_device"',
        'auth_mode = "BASIC"',
        'password = "must-not-exist"',
        'http_risk_accepted = false',
    ],
)
def test_transport_profile_rejects_open_or_unsafe_fields(tmp_path, field_value: str) -> None:
    path = tmp_path / "invalid-profile.toml"
    valid = [
        '[transport]',
        'selected_profile = "field-a"',
        '[[transport.profiles]]',
        'id = "field-a"',
        'targets = ["192.0.2.10"]',
        'component = "vendor_panasonic"',
        'protocol = "http"',
        'port = 8080',
        'auth_mode = "NATIVE_DIGEST_EXISTING"',
        'authorization_ref = "AUTH-2026-01"',
        'http_risk_accepted = true',
    ]
    field_name = field_value.split(" =", 1)[0]
    path.write_text("\n".join(
        line for line in valid if not line.startswith(field_name + " =")
    ) + "\n" + field_value + "\n", encoding="utf-8")

    with pytest.raises(ConfigurationError):
        load_settings(path)


def test_axis_public_profile_rejects_authenticated_http_before_session_creation() -> None:
    from cam_scanner.config.models import TransportProfile

    config = EffectiveConfig(
        transport_profiles=(TransportProfile(
            "axis-public", ("192.0.2.10",), "vendor_axis", "http", 8080,
            "PUBLIC_NONE", "AUTH-AXIS-01", True,
        ),)
    )
    selected = select_transport(
        config, ["192.0.2.10"], {"192.0.2.10": "vendor_axis"}, "axis-public"
    )
    transport = TargetTransportPolicy(
        CollectionContext(_target(), selected),
        session_factory=lambda: pytest.fail("unauthenticated policy must reject before I/O"),
    )

    with pytest.raises(TargetRejected):
        transport.request(
            "vendor_axis", "POST", "http://192.0.2.10:8080/axis-cgi/basicdeviceinfo.cgi",
            source="NATIVE", authenticated=True,
        )


@pytest.mark.parametrize(
    ("component", "auth_mode"),
    [
        ("vendor_hikvision", "NATIVE_DIGEST_EXISTING"),
        ("vendor_axis", "PUBLIC_NONE"),
        ("vendor_dahua", "NATIVE_DIGEST_EXISTING"),
        ("vendor_hanwha", "NATIVE_DIGEST_EXISTING"),
        ("vendor_panasonic", "NATIVE_DIGEST_EXISTING"),
    ],
)
def test_http_profiles_compile_only_for_the_five_declared_vendor_components(
    component: str, auth_mode: str,
) -> None:
    from cam_scanner.config.models import TransportProfile

    target = "192.0.2.10"
    config = EffectiveConfig(transport_profiles=(TransportProfile(
        "profile-a", (target,), component, "http", 8080,
        auth_mode, "AUTH-2026-01", True,
    ),))

    selected = select_transport(
        config, [target], {target: component}, "profile-a"
    )

    assert selected.transport_plan.rules == (
        TransportRule(target, component, "http", None, 8080),
    )


def test_transport_selection_summary_and_row_plans_require_exact_panasonic_model() -> None:
    from cam_scanner.config.models import TransportProfile

    target = "192.0.2.10"
    outside = "192.0.2.11"
    config = EffectiveConfig(transport_profiles=(TransportProfile(
        "panasonic-field", (target,), "vendor_panasonic", "http", 8080,
        "NATIVE_DIGEST_EXISTING", "AUTH-2026-01", True,
    ),))
    service = InventoryService(object(), config=config)
    rows = (
        TransportInputDescriptor(2, target, True, "Panasonic", ModelHint.parse("WV-S2531L")),
        TransportInputDescriptor(3, target, True, "Axis"),
        TransportInputDescriptor(4, outside, True, None),
        TransportInputDescriptor(5, outside, False, "Panasonic"),
    )

    options = service.transport_selection_options(rows)
    profile = next(item for item in options if item.selection_id == "panasonic-field")

    assert (profile.http_rows, profile.https_rows, profile.ineligible_rows) == (1, 1, 1)
    assert options[0].https_rows == 3
    chosen, blocked, metadata = service.prepare_transport_for_row(
        target, "Panasonic", "panasonic-field", model_hint=ModelHint.parse("WV-S2531L")
    )
    assert not blocked
    assert chosen.transport_plan.rules == (
        TransportRule(target, "vendor_panasonic", "http", None, 8080),
    )
    ineligible, blocked, ineligible_metadata = service.prepare_transport_for_row(
        target, "Axis", "panasonic-field", model_hint=ModelHint.parse("WV-S2531L")
    )
    assert blocked
    assert not ineligible.transport_plan.rules
    assert ineligible_metadata == metadata
    outside_config, outside_blocked, outside_metadata = service.prepare_transport_for_row(
        outside, None, "panasonic-field"
    )
    assert not outside_blocked
    assert outside_config.transport_plan.selection_id == "HTTPS_DEFAULT"
    assert outside_metadata == {"policy_id": "HTTPS_DEFAULT", "auth_mode": "NONE"}


def test_profile_ineligible_row_skips_collection_and_records_safe_local_policy() -> None:
    from cam_scanner.config.models import TransportProfile

    class NeverCollect:
        def collect(self, _target):
            pytest.fail("ineligible profile row must not start network collection")

    target_ip = "192.0.2.10"
    profile = TransportProfile(
        "panasonic-field", (target_ip,), "vendor_panasonic", "http", 8080,
        "NATIVE_DIGEST_EXISTING", "AUTH-2026-01", True,
    )
    service = InventoryService(NeverCollect(), config=EffectiveConfig(
        transport_profiles=(profile,),
    ))
    config, blocked, metadata = service.prepare_transport_for_row(
        target_ip, "Axis", profile.id
    )

    report, context = service.collect_execution(
        CameraTarget(target_ip, "viewer", "synthetic-secret"),
        manufacturer_hint="Axis",
        transport_config=config,
        transport_selection_id=profile.id,
        transport_selection_metadata=metadata,
        transport_selection_blocked=blocked,
    )
    attempt = report.attempts[0]
    assert blocked
    assert attempt.operation == "select_transport_policy"
    assert attempt.outcome == "SKIPPED"
    assert attempt.metadata == {
        "policy_id": "panasonic-field",
        "authorization_ref": "AUTH-2026-01",
        "auth_mode": "NATIVE_DIGEST_EXISTING",
    }
    assert "scheme" not in attempt.metadata
    assert "synthetic-secret" not in repr(report)
    assert context.auth.logical_attempts == 0
    context.close()


def test_transport_prompt_shows_only_safe_summary_and_supports_cancel() -> None:
    output: list[str] = []
    inputs = iter(("2",))
    ui = TerminalUI(input_fn=lambda _prompt: next(inputs), output_fn=output.append)
    choices = (
        TransportSelectionOption("HTTPS_DEFAULT", None, "NONE", 0, 1, 0),
        TransportSelectionOption(
            "panasonic-field", "AUTH-2026-01", "NATIVE_DIGEST_EXISTING", 1, 0, 0
        ),
    )

    assert ui.prompt_transport_selection(choices) == "panasonic-field"
    rendered = "\n".join(output)
    assert "AUTH-2026-01" not in rendered
    assert "panasonic-field" not in rendered
    assert "Perfil HTTP autorizado" in rendered
    assert "HTTP: 1 linha(s)" in rendered
    assert "192.0.2.10" not in rendered
    assert "secret" not in rendered.casefold()

    cancel = TerminalUI(input_fn=lambda _prompt: "0", output_fn=lambda _value: None)
    assert cancel.prompt_transport_selection(choices) is None
