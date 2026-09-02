"""Serialização de `StatusPayload`/`ErrorPayload` para a CLI e formatação humana em PT-BR.

Contrato formal em `specs/001-add-cli-interface/data-model.md` e
`specs/001-add-cli-interface/contracts/status-schema.json`. Note que `session.pid` **não** é
exposto — é detalhe interno de implementação, sem valor para um consumidor programático (ver
`data-model.md` § Entidades existentes reaproveitadas).
"""

from typing import Any

from controller.vpn_controller import VpnController
from core.models.connection_state import ConnectionState

_STATE_LABELS = {
    ConnectionState.DISCONNECTED: "Desconectado",
    ConnectionState.CONNECTING: "Conectando",
    ConnectionState.CONNECTED: "Conectado",
}


def _session_payload(controller: VpnController) -> dict[str, Any] | None:
    session = controller.session
    if session is None:
        return None
    return {
        "profile": session.profile,
        "iface": session.iface,
        "started_at": session.started_at,
        "elapsed_seconds": (
            session.elapsed_seconds() if session.started_at is not None else None
        ),
    }


def status_payload(controller: VpnController) -> dict[str, Any]:
    """Serializa o estado atual do `controller` conforme `status-schema.json`."""
    session = (
        _session_payload(controller)
        if controller.state == ConnectionState.CONNECTED
        else None
    )
    return {
        "state": controller.state.value,
        "selected_profile": controller.selected_profile,
        "profiles": list(controller.profiles),
        "session": session,
    }


def error_payload(code: str, message: str) -> dict[str, Any]:
    """Serializa uma falha conforme `status-schema.json` (`ErrorPayload`).

    `code` é estável, em inglês/snake_case, para o consumidor decidir programaticamente;
    `message` é legível, em português, só para exibição humana (Clarifications, spec.md).
    """
    return {"error": {"code": code, "message": message}}


def _format_elapsed(seconds: float) -> str:
    total = max(0, int(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def format_human(payload: dict[str, Any]) -> str:
    """Formata um `StatusPayload`/`ErrorPayload` como texto legível em PT-BR."""
    if "error" in payload:
        error = payload["error"]
        return f"Erro ({error['code']}): {error['message']}"

    state = payload["state"]
    try:
        state_label = _STATE_LABELS[ConnectionState(state)]
    except ValueError:
        state_label = state

    lines = [f"Estado: {state_label}"]
    lines.append(f"Perfil selecionado: {payload.get('selected_profile') or '(nenhum)'}")

    session = payload.get("session")
    if session is not None:
        lines.append(f"Perfil conectado: {session['profile']}")
        lines.append(f"Interface: {session.get('iface') or '(desconhecida)'}")
        elapsed = session.get("elapsed_seconds")
        if elapsed is not None:
            lines.append(f"Tempo conectado: {_format_elapsed(elapsed)}")

    profiles = payload.get("profiles") or []
    lines.append(f"Perfis disponíveis: {', '.join(profiles) if profiles else '(nenhum)'}")

    return "\n".join(lines)
