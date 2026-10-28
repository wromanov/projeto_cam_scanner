"""Terminal input and output boundary for the CLI workflows."""
from __future__ import annotations

import getpass
from collections.abc import Callable
from pathlib import Path

from cam_scanner.domain.enums import CollectionStatus, MainMenuChoice
from cam_scanner.domain.models import (
    CameraResult,
    CameraTarget,
    CollectionReport,
    ModelHint,
    parse_model_hint,
)
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
        self._model_hint_invalid = False
        self._pending_post_query_choice: MainMenuChoice | None = None

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

    def prompt_manufacturer_hint(self) -> str | None:
        """Ask for an optional declared manufacturer; blank keeps auto discovery."""
        value = self._input("Fabricante (opcional; vazio para identificação automática): ").strip()
        return value or None

    def prompt_model_hint(self) -> ModelHint | None:
        """Ask for an optional declared model; invalid text is silently discarded."""
        value = self._input("Modelo (opcional; vazio para identificação automática): ")
        if value.strip() in {item.value for item in MainMenuChoice}:
            self._pending_post_query_choice = MainMenuChoice(value.strip())
            self._model_hint_invalid = False
            return None
        self._model_hint_invalid = bool(value.strip(" ")) and parse_model_hint(value) is None
        return parse_model_hint(value)

    def prompt_transport_selection(self, options) -> str | None:
        """Select a precompiled transport policy using a credential-free summary."""
        available = [option for option in options if option.available]
        if (len(available) == 1 and available[0].selection_id == "HTTPS_DEFAULT"
                and len(options) == 1):
            return "HTTPS_DEFAULT"
        self._output("\nTransporte para esta execução")
        profile_index = 0
        for index, option in enumerate(available, start=1):
            if option.selection_id == "HTTPS_DEFAULT":
                label = "HTTPS verificado (padrão)"
            else:
                profile_index += 1
                label = f"Perfil HTTP autorizado {profile_index}"
            self._output(
                f"[{index}] {label} | "
                f"auth {option.auth_mode} | "
                f"HTTP: {option.http_rows} linha(s) | "
                f"HTTPS: {option.https_rows} linha(s) | "
                f"inelegíveis: {option.ineligible_rows}"
            )
        unavailable_index = 0
        for option in options:
            if not option.available:
                unavailable_index += 1
                label = (
                    "Regra HTTP legada"
                    if option.selection_id == "LEGACY_EXACT"
                    else f"Perfil HTTP configurado {unavailable_index}"
                )
                self._output(
                    f"Indisponível: {label} | HTTP: {option.http_rows} | "
                    f"HTTPS: {option.https_rows} | inelegíveis: {option.ineligible_rows} | "
                    "faltam referência de autorização e aceite vinculados."
                )
        if any(option.http_rows for option in available):
            self._output(
                "HTTP não oferece confidencialidade do tráfego; a seleção só vale para "
                "os alvos e componentes elegíveis desta execução."
            )
        self._output("[0] Cancelar sem iniciar a coleta")
        while True:
            value = self._input("Seleção: ").strip()
            if value == "0":
                return None
            if value.isascii() and value.isdigit():
                index = int(value)
                if 1 <= index <= len(available):
                    return available[index - 1].selection_id
            self._output("Opção inválida.")

    def show_transport_selection_cancelled(self) -> None:
        self._output("Seleção de transporte cancelada; nenhuma coleta foi iniciada.")

    @property
    def model_hint_invalid(self) -> bool:
        return self._model_hint_invalid

    @property
    def has_pending_post_query_choice(self) -> bool:
        return self._pending_post_query_choice is not None

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
        if report.model_hint is not None:
            self._output(f"Modelo declarado: {report.model_hint.declared}")
            if report.model_mismatch:
                self._output("Divergência entre modelo declarado e observado.")
        if report.conflicts:
            self._output("Conflitos preservados: " + ", ".join(report.conflicts))
        resolution = report.manufacturer_resolution
        if resolution is not None:
            for label, value in (
                ("Fabricante declarado", resolution.declared),
                ("Fabricante observado", resolution.observed),
                ("Fabricante resolvido", resolution.resolved),
            ):
                if value is not None:
                    self._output(f"{label}: {value}")
            if resolution.mismatch:
                self._output("Divergência entre fabricante declarado e observado.")
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
            policy_id = attempt.metadata.get("policy_id")
            if isinstance(policy_id, str):
                details.append(f"política {policy_id}")
            authorization_ref = attempt.metadata.get("authorization_ref")
            if isinstance(authorization_ref, str):
                details.append(f"referência {authorization_ref}")
            auth_mode = attempt.metadata.get("auth_mode")
            if isinstance(auth_mode, str):
                details.append(f"auth {auth_mode}")
            details.append(f"{attempt.duration:.3f} s")
            self._output(" - " + " | ".join(details))

    def post_query_menu(self) -> MainMenuChoice:
        self._output("\n[1] Pesquisar outra câmera")
        self._output("[2] Ir para modo MULTI")
        self._output("[3] Sair")
        if self._pending_post_query_choice is not None:
            choice = self._pending_post_query_choice
            self._pending_post_query_choice = None
            return choice
        while True:
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
