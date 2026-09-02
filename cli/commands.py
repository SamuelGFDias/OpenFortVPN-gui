"""Implementação dos subcomandos da CLI (`status`, `connect`, `disconnect`).

Cada função recebe um `VpnController` já montado (via `cli.wiring.build_controller()` em
produção, ou via fakes dos contratos ABC em teste — mesmo padrão de
`tests/test_vpn_controller.py`) e devolve um `dict` que já é um `StatusPayload` ou
`ErrorPayload` (`cli.formatting`) pronto para serialização. Nenhuma função aqui importa
`gi`/`Gtk`. Ver `specs/001-add-cli-interface/contracts/cli-commands.md` e `research.md` §3
(timeout de `connect`) e §4 (exit codes, resolvidos em `cli/dispatch.py`).
"""

import time
from typing import Any

from cli.formatting import error_payload, status_payload
from controller.vpn_controller import VpnController
from core.models.connection_state import ConnectionState

DEFAULT_CONNECT_TIMEOUT = 20.0
_POLL_INTERVAL_SECONDS = 1.0


def _is_sudo_denied(reason: str | None) -> bool:
    return bool(reason) and "sudo" in reason.lower()


def status_command(controller: VpnController) -> dict[str, Any]:
    """`status [--json]` — sempre sucesso, reflete o processo real no sistema."""
    controller.initialize()
    return status_payload(controller)


def connect_command(
    controller: VpnController, profile: str, timeout: float = DEFAULT_CONNECT_TIMEOUT
) -> dict[str, Any]:
    """`connect <perfil> [--timeout SEGUNDOS]` — bloqueia até confirmar ou falhar.

    Valida o perfil e o estado atual, dispara a conexão e faz *polling* de
    `controller.tick()` a cada 1s (mesmo mecanismo que a GUI já usa, ver
    `ui/application.py` `GLib.timeout_add_seconds(1, ...)`) até `CONNECTED`, um evento
    `connect_failed`, ou o `timeout` esgotar.
    """
    try:
        controller.initialize()

        if profile not in controller.profiles:
            return error_payload(
                "profile_not_found", f"Perfil '{profile}' não encontrado"
            )

        if controller.state != ConnectionState.DISCONNECTED:
            return error_payload(
                "already_connected", "Já existe uma conexão VPN ativa"
            )

        controller.select_profile(profile)
        initial_events = controller.start_connection()
        for event in initial_events:
            if event.kind == "connect_failed":
                if _is_sudo_denied(event.reason):
                    return error_payload(
                        "sudo_denied", "sudo negou permissão para iniciar a conexão"
                    )
                reason = event.reason or "motivo desconhecido"
                return error_payload("internal_error", f"Falha ao conectar: {reason}")

        deadline = time.monotonic() + timeout
        while True:
            events = controller.tick()
            for event in events:
                if event.kind == "connected":
                    return status_payload(controller)
                if event.kind == "connect_failed":
                    if _is_sudo_denied(event.reason):
                        return error_payload(
                            "sudo_denied",
                            "sudo negou permissão para iniciar a conexão",
                        )
                    reason = event.reason or "motivo desconhecido"
                    return error_payload(
                        "internal_error", f"Falha ao conectar: {reason}"
                    )

            if controller.state == ConnectionState.CONNECTED:
                return status_payload(controller)

            if time.monotonic() >= deadline:
                return error_payload(
                    "connect_timeout",
                    "Tempo esgotado aguardando a conexão subir — "
                    "verifique com 'status' se ela subiu por conta própria",
                )

            time.sleep(_POLL_INTERVAL_SECONDS)
    except Exception as exc:  # pragma: no cover - defensivo, ver FR-009/data-model.md
        return error_payload("internal_error", f"Erro inesperado: {exc}")


def disconnect_command(controller: VpnController) -> dict[str, Any]:
    """`disconnect` — encerra a conexão ativa, mesmo se iniciada por outro processo."""
    try:
        controller.initialize()

        if controller.state == ConnectionState.DISCONNECTED:
            return error_payload(
                "not_connected", "Nenhuma conexão VPN ativa para desconectar"
            )

        controller.stop_connection()
        return status_payload(controller)
    except Exception as exc:
        if _is_sudo_denied(str(exc)):
            return error_payload(
                "sudo_denied", "sudo negou permissão para desconectar"
            )
        return error_payload("internal_error", f"Erro inesperado: {exc}")  # pragma: no cover
