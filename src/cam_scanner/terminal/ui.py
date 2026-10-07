"""Terminal input and output boundary for the CLI workflows."""
from __future__ import annotations

import getpass
from collections.abc import Callable

from cam_scanner.domain.enums import CollectionStatus, MainMenuChoice
from cam_scanner.domain.models import CameraResult, CameraTarget


class TerminalUI:
    """Keep interactive terminal handling out of the application workflows."""

    def __init__(
        self,
        input_fn: Callable[[str], str] | None = None,
        password_fn: Callable[[str], str] | None = None,
        output_fn: Callable[[str], object] | None = None,
    ) -> None:
        self._input = input_fn or input
        self._password = password_fn or getpass.getpass
        self._output = output_fn or print

    def main_menu(self) -> MainMenuChoice:
        while True:
            self._output("\nCAM SCANNER")
            self._output("[1] SINGLE")
            self._output("[2] MULTI")
            self._output("[3] Sair")
            choice = self._input("Escolha uma opção: ").strip()
            if choice in {item.value for item in MainMenuChoice}:
                return MainMenuChoice(choice)
            self._output("Opção inválida. Escolha 1, 2 ou 3.")

    def prompt_camera_target(self) -> CameraTarget:
        ip = self._input("IP da câmera: ").strip()
        username = self._input("Username: ").strip()
        password = self._password("Password: ")
        return CameraTarget(ip=ip, username=username, password=password)

    def render_result(self, result: CameraResult) -> None:
        self._output("\nResultado da consulta")
        self._output(f"IP: {result.ip}")
        self._output(f"Status: {result.status.value}")
        if result.status is CollectionStatus.FAILED:
            if result.error_code is not None:
                self._output(f"Código: {result.error_code.value}")
            self._output(f"Erro: {result.error_message}")
            return

        for label, value in (
            ("Fabricante", result.manufacturer),
            ("Modelo", result.model),
            ("Número de série", result.serial),
            ("Firmware", result.firmware),
        ):
            if value is not None:
                self._output(f"{label}: {value}")
        self._output(f"Duração: {result.duration:.3f} s")

    def post_query_menu(self) -> MainMenuChoice:
        while True:
            self._output("\n[1] Pesquisar outra câmera")
            self._output("[2] Ir para modo MULTI")
            self._output("[3] Sair")
            choice = self._input("Escolha uma opção: ").strip()
            if choice in {item.value for item in MainMenuChoice}:
                return MainMenuChoice(choice)
            self._output("Opção inválida. Escolha 1, 2 ou 3.")

    def show_multi_unavailable(self) -> None:
        self._output("O modo MULTI ainda não está disponível nesta versão.")

    def show_unexpected_error(self) -> None:
        self._output("Ocorreu um erro inesperado. Consulte o log sanitizado para diagnóstico.")

    def show_interrupted(self) -> None:
        self._output("Execução interrompida pelo usuário.")
