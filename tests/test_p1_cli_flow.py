"""CLI integration tests using a deterministic in-memory ONVIF device."""
import importlib
import logging

import onvif


def test_cli_entrypoint_runs_single_flow_without_printing_password(monkeypatch, capsys) -> None:
    calls: list[str] = []
    client_options: dict[str, object] = {}

    class FakeDeviceService:
        def GetDeviceInformation(self) -> dict[str, str]:
            calls.append("GetDeviceInformation")
            return {
                "Manufacturer": "Example Cameras",
                "Model": "Model A",
                "SerialNumber": "serial-1",
                "FirmwareVersion": "1.2.3",
            }

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            client_options.update(kwargs)

        def devicemgmt(self) -> FakeDeviceService:
            return FakeDeviceService()

    main_module = importlib.import_module("cam_scanner.main")
    monkeypatch.setattr(onvif, "ONVIFClient", FakeClient)
    monkeypatch.setattr(main_module, "configure_logging", lambda: logging.getLogger("test-cli"))
    answers = iter(["1", "192.0.2.10", "operator", "3"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    monkeypatch.setattr("getpass.getpass", lambda _prompt: "private-password")

    assert main_module.main() == 0

    output = capsys.readouterr().out
    assert calls == ["GetDeviceInformation"]
    assert client_options["password"] == "private-password"
    assert client_options["cache"] is onvif.CacheMode.NONE
    assert "Example Cameras" in output
    assert "serial-1" in output
    assert "private-password" not in output
    assert "[1] Pesquisar outra câmera" in output
    assert "Traceback" not in output


def test_cli_handles_authentication_failure_without_a_traceback(monkeypatch, capsys) -> None:
    from zeep.exceptions import Fault

    class FakeDeviceService:
        def GetDeviceInformation(self) -> dict[str, str]:
            raise Fault("NotAuthorized")

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            pass

        def devicemgmt(self) -> FakeDeviceService:
            return FakeDeviceService()

    main_module = importlib.import_module("cam_scanner.main")
    monkeypatch.setattr(onvif, "ONVIFClient", FakeClient)
    monkeypatch.setattr(main_module, "configure_logging", lambda: logging.getLogger("test-cli-auth"))
    answers = iter(["1", "192.0.2.10", "operator", "3"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    monkeypatch.setattr("getpass.getpass", lambda _prompt: "private-password")

    assert main_module.main() == 0

    output = capsys.readouterr().out
    assert "A câmera recusou a autenticação." in output
    assert "private-password" not in output
    assert "Traceback" not in output
    assert "[3] Sair" in output


def test_post_query_menu_repeats_single_and_routes_multi_to_controller(monkeypatch, capsys) -> None:
    calls: list[str] = []

    class FakeDeviceService:
        def GetDeviceInformation(self) -> dict[str, str]:
            calls.append("GetDeviceInformation")
            return {"Manufacturer": "Example", "Model": "Model A"}

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            pass

        def devicemgmt(self) -> FakeDeviceService:
            return FakeDeviceService()

    main_module = importlib.import_module("cam_scanner.main")
    monkeypatch.setattr(onvif, "ONVIFClient", FakeClient)
    monkeypatch.setattr(main_module, "configure_logging", lambda: logging.getLogger("test-cli-nav"))
    answers = iter(
        [
            "1",
            "192.0.2.10",
            "operator",
            "1",
            "192.0.2.11",
            "operator",
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
    assert output.count("O modo MULTI ainda não está disponível nesta versão.") == 2
    assert "192.0.2.11" in output
    assert "private-password" not in output
