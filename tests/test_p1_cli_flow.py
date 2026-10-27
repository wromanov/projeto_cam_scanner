"""CLI integration tests using a deterministic in-memory ONVIF device."""

import importlib
import logging


def _install_controlled_client(monkeypatch, factory) -> None:
    """Replace only the controlled client boundary; keep routing and workflows real."""
    monkeypatch.setattr("cam_scanner.cameras.preauth.ControlledOnvifClient", factory)
    monkeypatch.setattr("cam_scanner.cameras.onvif.adapter.ControlledOnvifClient", factory)


def _install_unsupported_snapshots(monkeypatch, main_module) -> None:
    from cam_scanner.snapshot.service import SnapshotCaptureError, SnapshotFailure, SnapshotService

    class UnsupportedProvider:
        def capture(self, _target, **_kwargs):
            raise SnapshotCaptureError(SnapshotFailure.UNSUPPORTED)

    monkeypatch.setattr(
        main_module,
        "SnapshotService",
        lambda: SnapshotService(UnsupportedProvider(), UnsupportedProvider(), UnsupportedProvider()),
    )


def test_cli_entrypoint_runs_single_flow_without_printing_password(monkeypatch, capsys) -> None:
    calls: list[str] = []
    client_options: list[dict[str, object]] = []

    class FakeDeviceService:
        def __init__(self, context) -> None:
            self.context = context

        def GetCapabilities(self, **_kwargs: object) -> dict[str, str]:
            calls.append("GetCapabilities")
            return {"Manufacturer": "Example Cameras"}

        def GetDeviceInformation(self) -> dict[str, str]:
            calls.append("GetDeviceInformation")
            self.context.auth.observe_http(200, "ONVIF", authenticated=True)
            return {
                "Manufacturer": "Example Cameras",
                "Model": "Model A",
                "SerialNumber": "serial-1",
                "FirmwareVersion": "1.2.3",
            }

    class FakeClient:
        def __init__(self, context, *, authenticated: bool) -> None:
            self.context = context
            client_options.append({"authenticated": authenticated,
                                   "username": context.target.username if authenticated else None,
                                   "password": context.target.password if authenticated else None})

        def devicemgmt(self) -> FakeDeviceService:
            return FakeDeviceService(self.context)

    main_module = importlib.import_module("cam_scanner.main")
    _install_controlled_client(monkeypatch, FakeClient)
    _install_unsupported_snapshots(monkeypatch, main_module)
    monkeypatch.setattr(main_module, "configure_logging", lambda **_kwargs: logging.getLogger("test-cli"))
    answers = iter(["1", "192.0.2.10", "operator", "", "3"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    monkeypatch.setattr("getpass.getpass", lambda _prompt: "private-password")

    assert main_module.main() == 0

    output = capsys.readouterr().out
    assert calls == ["GetCapabilities", "GetDeviceInformation"]
    assert client_options[0]["authenticated"] is False
    assert client_options[0]["password"] is None
    assert client_options[1]["authenticated"] is True
    assert client_options[1]["password"] == "private-password"
    assert "Example Cameras" in output
    assert "serial-1" in output
    assert "private-password" not in output
    assert "[1] Pesquisar outra câmera" in output
    assert "Traceback" not in output


def test_cli_handles_authentication_failure_without_a_traceback(monkeypatch, capsys) -> None:
    from zeep.exceptions import Fault

    class FakeDeviceService:
        def __init__(self, context) -> None:
            self.context = context

        def GetCapabilities(self, **_kwargs: object) -> None:
            return None

        def GetDeviceInformation(self) -> dict[str, str]:
            self.context.auth.observe_soap("NotAuthorized", authenticated=True)
            raise Fault("NotAuthorized")

    class FakeClient:
        def __init__(self, context, *, authenticated: bool) -> None:
            self.context = context

        def devicemgmt(self) -> FakeDeviceService:
            return FakeDeviceService(self.context)

    main_module = importlib.import_module("cam_scanner.main")
    _install_controlled_client(monkeypatch, FakeClient)
    _install_unsupported_snapshots(monkeypatch, main_module)
    monkeypatch.setattr(main_module, "configure_logging", lambda **_kwargs: logging.getLogger("test-cli-auth"))
    answers = iter(["1", "192.0.2.10", "operator", "", "3"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    monkeypatch.setattr("getpass.getpass", lambda _prompt: "private-password")

    assert main_module.main() == 0

    output = capsys.readouterr().out
    assert "A câmera retornou um erro ONVIF." in output
    assert "private-password" not in output
    assert "Traceback" not in output
    assert "[3] Sair" in output


def test_cli_startup_failure_without_log_handler_keeps_diagnostic_off_terminal(
    monkeypatch, capsys
) -> None:
    main_module = importlib.import_module("cam_scanner.main")
    logger = logging.getLogger("cam_scanner")
    unexpected_errors: list[bool] = []

    class FakeUI:
        def show_unexpected_error(self) -> None:
            unexpected_errors.append(True)

    def fail_logging(**_kwargs: object) -> None:
        raise OSError("synthetic unwritable log path")

    monkeypatch.setattr(logger, "handlers", [])
    monkeypatch.setattr(logger, "propagate", False)
    monkeypatch.setattr(main_module, "TerminalUI", FakeUI)
    monkeypatch.setattr(main_module, "load_settings", lambda: object())
    monkeypatch.setattr(main_module, "configure_logging", fail_logging)
    monkeypatch.setattr(main_module, "close_logging", lambda: None)

    assert main_module.main() == 1

    captured = capsys.readouterr()
    assert unexpected_errors == [True]
    assert captured.out == ""
    assert captured.err == ""


def test_cli_preserves_preauth_evidence_as_partial_success_after_onvif_auth_failure(
    monkeypatch, capsys
) -> None:
    from zeep.exceptions import Fault

    clients: list[dict[str, object]] = []
    calls: list[str] = []

    class PreAuthDevice:
        def GetCapabilities(self, **_kwargs: object) -> dict[str, object]:
            calls.append("GetCapabilities")
            return {"Manufacturer": "Hikvision"}

        def GetSystemDateAndTime(self) -> dict[str, str]:
            calls.append("GetSystemDateAndTime")
            return {"Time": "read-only"}

    class AuthDevice:
        def GetDeviceInformation(self) -> dict[str, str]:
            calls.append("GetDeviceInformation")
            _AUTH_CONTEXT.auth.observe_soap("NotAuthorized", authenticated=True)
            raise Fault("NotAuthorized")

    class FakeClient:
        def __init__(self, context, *, authenticated: bool) -> None:
            global _AUTH_CONTEXT
            _AUTH_CONTEXT = context
            clients.append({"username": context.target.username if authenticated else None,
                            "password": context.target.password if authenticated else None,
                            "authenticated": authenticated})

        def devicemgmt(self) -> PreAuthDevice | AuthDevice:
            if clients[-1]["authenticated"]:
                return AuthDevice()
            return PreAuthDevice()

    main_module = importlib.import_module("cam_scanner.main")

    class UnsupportedHikvisionAdapter:
        def collect_report(self, target):
            from cam_scanner.domain.models import CollectionAttempt, CollectionReport

            report = CollectionReport().with_attempt(
                CollectionAttempt(
                    protocol="HTTP",
                    operation="GET /ISAPI/System/deviceInfo",
                    stage="HTTP",
                    outcome="SKIPPED",
                    error_category="ENDPOINT_UNSUPPORTED",
                )
            )
            return report

    from cam_scanner.cameras.registry import AdapterRegistry

    registry = AdapterRegistry()
    registry.register("Hikvision", UnsupportedHikvisionAdapter())
    monkeypatch.setattr(main_module, "build_default_registry", lambda: registry)
    _install_controlled_client(monkeypatch, FakeClient)
    _install_unsupported_snapshots(monkeypatch, main_module)
    monkeypatch.setattr(main_module, "configure_logging", lambda **_kwargs: logging.getLogger("test-cli-partial"))
    answers = iter(["1", "192.0.2.10", "operator", "", "3"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    monkeypatch.setattr("getpass.getpass", lambda _prompt: "private-password")

    assert main_module.main() == 0

    output = capsys.readouterr().out
    assert calls == ["GetCapabilities", "GetDeviceInformation"]
    assert "Status: PARTIAL_SUCCESS" in output
    assert "Fabricante: Hikvision" in output
    assert "A câmera forneceu evidência pré-autenticação" in output
    assert "Conflitos preservados:" not in output
    assert "private-password" not in output
    assert clients[0]["username"] is None and clients[0]["password"] is None
    assert clients[1]["password"] == "private-password"


def test_post_query_menu_repeats_single_and_routes_multi_to_controller(monkeypatch, capsys) -> None:
    calls: list[str] = []

    class FakeDeviceService:
        def __init__(self, context) -> None:
            self.context = context

        def GetCapabilities(self, **_kwargs: object) -> dict[str, str]:
            return {"Manufacturer": "Example"}

        def GetDeviceInformation(self) -> dict[str, str]:
            calls.append("GetDeviceInformation")
            self.context.auth.observe_http(200, "ONVIF", authenticated=True)
            return {"Manufacturer": "Example", "Model": "Model A"}

    class FakeClient:
        def __init__(self, context, *, authenticated: bool) -> None:
            self.context = context

        def devicemgmt(self) -> FakeDeviceService:
            return FakeDeviceService(self.context)

    main_module = importlib.import_module("cam_scanner.main")
    _install_controlled_client(monkeypatch, FakeClient)
    _install_unsupported_snapshots(monkeypatch, main_module)
    monkeypatch.setattr(main_module, "configure_logging", lambda **_kwargs: logging.getLogger("test-cli-nav"))
    multi_calls: list[str] = []

    class FakeMultiWorkflow:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def run(self) -> None:
            multi_calls.append("run")

    monkeypatch.setattr(main_module, "MultiWorkflow", FakeMultiWorkflow)
    answers = iter(
        [
            "1",
            "192.0.2.10",
            "operator",
            "",
            "1",
            "192.0.2.11",
            "operator",
            "",
            "2",
            "2",
            "3",
        ]
    )
    password_calls: list[str] = []

    def get_password(_prompt: str) -> str:
        password_calls.append("called")
        return "private-password"

    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    monkeypatch.setattr("getpass.getpass", get_password)

    assert main_module.main() == 0

    output = capsys.readouterr().out
    assert calls == ["GetDeviceInformation", "GetDeviceInformation"]
    assert len(password_calls) == 2
    assert multi_calls == ["run", "run"]
    assert "192.0.2.11" in output
    assert "private-password" not in output


def test_cli_single_success_includes_offline_snapshot_without_printing_password(
    monkeypatch, capsys
) -> None:
    from cam_scanner.domain.enums import CollectionStatus
    from cam_scanner.domain.models import CameraResult, CollectionReport
    from cam_scanner.snapshot.service import SnapshotService

    snapshot_targets: list[str] = []

    class FakeCollector:
        def collect_report(self, target, *, context):
            context.auth.begin("ONVIF", "initial")
            context.auth.observe_http(200, "ONVIF", authenticated=True)
            return CollectionReport.from_camera_result(CameraResult(
                ip=target.ip,
                status=CollectionStatus.SUCCESS,
                manufacturer="Example Cameras",
                model="Model A",
                serial="serial-1",
                duration=0.0,
            ))

    class SnapshotProvider:
        def capture(self, target, **_context):
            snapshot_targets.append(target.ip)
            return b"synthetic-frame"

    class UnusedProvider:
        def capture(self, _target, **_context):
            raise AssertionError("unexpected snapshot fallback")

    main_module = importlib.import_module("cam_scanner.main")
    monkeypatch.setattr(
        main_module,
        "VendorFirstCollector",
        lambda **_kwargs: FakeCollector(),
    )
    monkeypatch.setattr(
        main_module,
        "SnapshotService",
        lambda: SnapshotService(
            SnapshotProvider(),
            UnusedProvider(),
            UnusedProvider(),
            image_processor=lambda _raw: (b"processed-jpeg", 320, 160),
        ),
    )
    monkeypatch.setattr(main_module, "configure_logging", lambda **_kwargs: logging.getLogger("test-cli-snapshot"))
    answers = iter(["1", "192.0.2.10", "operator", "", "3"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    monkeypatch.setattr("getpass.getpass", lambda _prompt: "private-password")

    assert main_module.main() == 0

    output = capsys.readouterr().out
    assert snapshot_targets == ["192.0.2.10"]
    assert "Status: SUCCESS" in output
    assert "Snapshot: disponível (320x160, ONVIF_HTTP)" in output
    assert "private-password" not in output
    assert "Traceback" not in output
