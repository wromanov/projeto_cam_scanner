"""Terminal input and output boundary for the CLI workflows."""
from __future__ import annotations

import getpass
from collections.abc import Callable
from pathlib import Path

from cam_scanner.domain.enums import CollectionStatus, MainMenuChoice
from cam_scanner.domain.models import CameraResult, CameraTarget, CollectionReport
from cam_scanner.snapshot.service import SnapshotResult


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

    def render_result(self, result: CameraResult, snapshot: SnapshotResult | None = None) -> None:
        self._output("\nResultado da consulta")
        self._output(f"IP: {result.ip}")
        self._output(f"Status: {result.status.value}")
        if result.status is CollectionStatus.FAILED:
            if result.error_code is not None:
                self._output(f"Código: {result.error_code.value}")
            self._output(f"Erro: {result.error_message}")
            return

        if result.error_code is not None:
            self._output(f"Código: {result.error_code.value}")
        if result.error_message is not None:
            self._output(f"Aviso: {result.error_message}")

        for label, value in (
            ("Fabricante", result.manufacturer),
            ("Modelo", result.model),
            ("Número de série", result.serial),
            ("Firmware", result.firmware),
        ):
            if value is not None:
                self._output(f"{label}: {value}")
        self._output(f"Duração: {result.duration:.3f} s")
        if result.collection_method is not None:
            self._output(f"Método: {result.collection_method.value}")
        if snapshot is not None:
            if snapshot.successful:
                self._output(f"Snapshot: disponível ({snapshot.width}x{snapshot.height}, {snapshot.method.value})")
            else:
                self._output("Snapshot: indisponível; os dados de identidade foram preservados.")

    def render_report(
        self, report: CollectionReport, *, ip: str, duration: float, snapshot: SnapshotResult | None = None
    ) -> None:
        """Render the P1-compatible result and safe per-operation diagnostics."""
        self.render_result(report.to_camera_result(ip, duration=duration), snapshot)
        if report.conflicts:
            self._output("Conflitos preservados: " + ", ".join(report.conflicts))
        if not report.attempts:
            return
        self._output("Diagnósticos da coleta")
        for attempt in report.attempts:
            protocol = attempt.protocol or "local"
            outcome = attempt.error_category or attempt.outcome
            details = [f"{protocol}.{attempt.operation}", attempt.stage, outcome]
            if attempt.http_status is not None:
                details.append(f"HTTP {attempt.http_status}")
            if attempt.protocol_code is not None:
                details.append(f"código {attempt.protocol_code}")
            if attempt.retry_count:
                details.append(f"retries {attempt.retry_count}")
            details.append(f"{attempt.duration:.3f} s")
            self._output(" - " + " | ".join(details))

    def post_query_menu(self) -> MainMenuChoice:
        while True:
            self._output("\n[1] Pesquisar outra câmera")
            self._output("[2] Ir para modo MULTI")
            self._output("[3] Sair")
            choice = self._input("Escolha uma opção: ").strip()
            if choice in {item.value for item in MainMenuChoice}:
                return MainMenuChoice(choice)
            self._output("Opção inválida. Escolha 1, 2 ou 3.")

    def prompt_multi_input_path(self) -> str:
        return self._input("Caminho da planilha XLSX de entrada: ").strip()

    def prompt_multi_output_path(self, default_path: str) -> str:
        value = self._input(f"Caminho do XLSX de saída [{default_path}]: ").strip()
        return value or default_path

    def show_multi_error(self, message: str) -> None:
        self._output(f"MULTI não concluído: {message}")

    def show_multi_complete(
        self, path: str | Path, camera_count: int, *, failed: int = 0
    ) -> None:
        self._output(
            f"MULTI concluído: {camera_count} linhas processadas; "
            f"{camera_count - failed} concluídas, {failed} falhas."
        )
        self._output(f"Arquivo gerado: {path}")

    def show_multi_unavailable(self) -> None:
        self._output("O modo MULTI ainda não está disponível nesta versão.")

    def show_unexpected_error(self) -> None:
        self._output("Ocorreu um erro inesperado. Consulte o log sanitizado para diagnóstico.")

    def show_interrupted(self) -> None:
        self._output("Execução interrompida pelo usuário.")
