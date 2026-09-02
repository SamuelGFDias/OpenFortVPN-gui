from cli.formatting import error_payload, format_human, status_payload
from controller.vpn_controller import VpnController
from core.interfaces.profile_source import ProfileSource
from core.interfaces.state_store import AppStateStore, HistoryStore
from core.interfaces.tunnel_state_detector import TunnelStateDetector
from core.interfaces.vpn_backend import VpnBackend
from core.models.connect_outcome import ConnectOutcome

# Mesmo padrão de fakes de tests/test_vpn_controller.py (Princípio V da constitution:
# testes por contrato ABC, nunca contra GTK/display).


class FakeVpnBackend(VpnBackend):
    def __init__(self, running=False, start_pid=100, outcome=None):
        self.running = running
        self.start_pid = start_pid
        self.outcome = outcome
        self.start_calls = []
        self.stop_calls = []

    def start(self, profile_path: str) -> int:
        self.start_calls.append(profile_path)
        self.running = True
        return self.start_pid

    def stop(self, pid):
        self.stop_calls.append(pid)
        self.running = False

    def is_running(self, pid) -> bool:
        return self.running

    def poll_outcome(self, pid) -> ConnectOutcome | None:
        return self.outcome


class FakeTunnelStateDetector(TunnelStateDetector):
    def __init__(self, iface=None, present=None):
        self.iface = iface
        self._present = set(present) if present is not None else None

    def snapshot(self) -> frozenset[str]:
        return frozenset({self.iface}) if self.iface else frozenset()

    def detect_new_interface(self, baseline: frozenset[str]):
        current = frozenset({self.iface}) if self.iface else frozenset()
        new = current - baseline
        return next(iter(new), None)

    def is_interface_present(self, name: str) -> bool:
        if self._present is not None:
            return name in self._present
        return name == self.iface


class FakeProfileSource(ProfileSource):
    def __init__(self, profiles):
        self._profiles = profiles

    def list_profiles(self) -> list[str]:
        return list(self._profiles)

    def resolve_path(self, name: str) -> str:
        return f"/etc/openfortivpn/{name}"

    def is_user_profile(self, name: str) -> bool:
        return False


class FakeAppStateStore(AppStateStore):
    def __init__(self, last_profile=None, active_session=None):
        self._last_profile = last_profile
        self._active_session = active_session
        self.saved_sessions = []
        self.cleared = 0

    def load_last_profile(self):
        return self._last_profile

    def save_last_profile(self, profile):
        self._last_profile = profile

    def load_active_session(self):
        return self._active_session

    def save_active_session(self, session):
        self._active_session = session
        self.saved_sessions.append(session)

    def clear_active_session(self):
        self._active_session = None
        self.cleared += 1


class FakeHistoryStore(HistoryStore):
    def __init__(self):
        self.records = []

    def load(self):
        return list(self.records)

    def append(self, record):
        self.records.append(record)


def make_controller(
    running=False,
    iface=None,
    profiles=("matriz.conf",),
    last_profile=None,
    active_session=None,
):
    backend = FakeVpnBackend(running=running)
    detector = FakeTunnelStateDetector(iface=iface)
    profile_source = FakeProfileSource(profiles)
    app_state_store = FakeAppStateStore(last_profile=last_profile, active_session=active_session)
    history_store = FakeHistoryStore()
    controller = VpnController(
        backend=backend,
        detector=detector,
        profile_source=profile_source,
        app_state_store=app_state_store,
        history_store=history_store,
    )
    return controller, backend, detector, app_state_store, history_store


# ---------------------------------------------------------------------------
# status_payload() — schema (T008)
# ---------------------------------------------------------------------------


def test_status_payload_schema_desconectado():
    controller, *_ = make_controller()

    payload = status_payload(controller)

    assert set(payload.keys()) == {"state", "selected_profile", "profiles", "session"}
    assert payload["state"] == "disconnected"
    assert payload["selected_profile"] == "matriz.conf"
    assert payload["profiles"] == ["matriz.conf"]
    assert payload["session"] is None


def test_status_payload_schema_conectado_nao_expoe_pid():
    controller, backend, detector, *_ = make_controller()
    controller.start_connection()
    detector.iface = "tun0"
    controller.tick()
    assert controller.state.value == "connected"

    payload = status_payload(controller)

    assert payload["state"] == "connected"
    session = payload["session"]
    assert session is not None
    assert set(session.keys()) == {"profile", "iface", "started_at", "elapsed_seconds"}
    assert "pid" not in session
    assert session["profile"] == "matriz.conf"
    assert session["iface"] == "tun0"
    assert session["started_at"] is not None
    assert session["elapsed_seconds"] is not None


def test_status_payload_schema_conectando_sem_sessao():
    controller, *_ = make_controller(running=True, iface=None)
    controller.initialize()
    assert controller.state.value == "connecting"

    payload = status_payload(controller)

    assert payload["state"] == "connecting"
    assert payload["session"] is None


def test_status_human_text():
    controller, *_ = make_controller()

    text = format_human(status_payload(controller))

    assert "Desconectado" in text
    assert "matriz.conf" in text


def test_status_human_text_conectado_inclui_perfil_e_interface():
    controller, backend, detector, *_ = make_controller()
    controller.start_connection()
    detector.iface = "tun0"
    controller.tick()

    text = format_human(status_payload(controller))

    assert "Conectado" in text
    assert "matriz.conf" in text
    assert "tun0" in text


# ---------------------------------------------------------------------------
# error_payload() — schema (T012, T016)
# ---------------------------------------------------------------------------


def test_error_payload_codes_connect():
    for code in ("profile_not_found", "already_connected", "connect_timeout", "sudo_denied"):
        payload = error_payload(code, "mensagem legível em português")

        assert set(payload.keys()) == {"error"}
        assert set(payload["error"].keys()) == {"code", "message"}
        assert payload["error"]["code"] == code
        assert payload["error"]["message"] == "mensagem legível em português"


def test_error_payload_not_connected():
    payload = error_payload("not_connected", "Nenhuma conexão VPN ativa para desconectar")

    assert payload == {
        "error": {
            "code": "not_connected",
            "message": "Nenhuma conexão VPN ativa para desconectar",
        }
    }


def test_format_human_erro_inclui_code_e_message():
    payload = error_payload("not_connected", "Nenhuma conexão VPN ativa para desconectar")

    text = format_human(payload)

    assert "not_connected" in text
    assert "Nenhuma conexão VPN ativa para desconectar" in text
