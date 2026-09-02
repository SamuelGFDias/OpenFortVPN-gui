from cli.commands import connect_command, disconnect_command, status_command
from controller.vpn_controller import VpnController
from core.interfaces.profile_source import ProfileSource
from core.interfaces.state_store import AppStateStore, HistoryStore
from core.interfaces.tunnel_state_detector import TunnelStateDetector
from core.interfaces.vpn_backend import VpnBackend
from core.models.connect_outcome import ConnectOutcome
from core.models.connection_session import ConnectionSession

# Mesmo padrão de fakes de tests/test_vpn_controller.py (Princípio V da constitution:
# testes por contrato ABC, nunca contra GTK/display/openfortivpn real).


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
# status_command() — T007
# ---------------------------------------------------------------------------


def test_status_disconnected():
    controller, backend, detector, *_ = make_controller(running=False)

    payload = status_command(controller)

    assert payload["state"] == "disconnected"
    assert payload["session"] is None


def test_status_connecting():
    controller, backend, detector, *_ = make_controller(running=True, iface=None)

    payload = status_command(controller)

    assert payload["state"] == "connecting"
    assert payload["session"] is None


def test_status_connected():
    sessao_previa = ConnectionSession(profile="matriz.conf", iface="tun0", started_at=100.0)
    controller, backend, detector, *_ = make_controller(
        running=True, iface="tun0", active_session=sessao_previa
    )

    payload = status_command(controller)

    assert payload["state"] == "connected"
    assert payload["session"]["profile"] == "matriz.conf"
    assert payload["session"]["iface"] == "tun0"


# ---------------------------------------------------------------------------
# connect_command() — T011
# ---------------------------------------------------------------------------


def test_connect_success(monkeypatch):
    controller, backend, detector, *_ = make_controller()

    def fake_sleep(_seconds):
        # Simula a interface tun* aparecendo entre um tick() e o próximo, sem
        # esperar 1s de verdade — ver research.md §3 / tasks.md T011.
        detector.iface = "tun0"

    monkeypatch.setattr("cli.commands.time.sleep", fake_sleep)

    payload = connect_command(controller, "matriz.conf", timeout=5.0)

    assert "error" not in payload
    assert payload["state"] == "connected"
    assert payload["session"]["profile"] == "matriz.conf"
    assert payload["session"]["iface"] == "tun0"
    assert backend.start_calls == ["/etc/openfortivpn/matriz.conf"]


def test_connect_profile_not_found():
    controller, backend, detector, *_ = make_controller(profiles=("matriz.conf",))

    payload = connect_command(controller, "inexistente.conf", timeout=1.0)

    assert payload["error"]["code"] == "profile_not_found"
    assert backend.start_calls == []


def test_connect_already_connected():
    controller, backend, detector, *_ = make_controller()
    controller.start_connection()
    detector.iface = "tun0"
    controller.tick()
    assert controller.state.value == "connected"

    payload = connect_command(controller, "matriz.conf", timeout=1.0)

    assert payload["error"]["code"] == "already_connected"
    # não inicia um segundo processo openfortivpn
    assert backend.start_calls == ["/etc/openfortivpn/matriz.conf"]


def test_connect_timeout(monkeypatch):
    controller, backend, detector, *_ = make_controller()
    # backend.running fica True após start() (processo "subindo"), mas nenhuma
    # interface tun*/ppp* jamais aparece — timeout pequeno, sleep mockado, sem
    # esperar 1s real dentro do teste (tasks.md T011).
    monkeypatch.setattr("cli.commands.time.sleep", lambda _seconds: None)

    payload = connect_command(controller, "matriz.conf", timeout=0.05)

    assert payload["error"]["code"] == "connect_timeout"
    assert backend.start_calls == ["/etc/openfortivpn/matriz.conf"]


# ---------------------------------------------------------------------------
# disconnect_command() — T015
# ---------------------------------------------------------------------------


def test_disconnect_success():
    controller, backend, detector, app_state_store, history_store = make_controller()
    controller.start_connection()
    detector.iface = "tun0"
    controller.tick()
    assert controller.state.value == "connected"

    payload = disconnect_command(controller)

    assert "error" not in payload
    assert payload["state"] == "disconnected"
    assert payload["session"] is None
    # disconnect_command() sempre chama controller.initialize() antes de
    # stop_connection() (research.md §6) — o reattach reconstrói a sessão sem PID,
    # então mesmo desconectando na mesma invocação que conectou, a CLI cai no
    # fallback "matar por nome" (pid=None), nunca no PID original.
    assert backend.stop_calls == [None]
    assert len(history_store.records) == 1


def test_disconnect_not_connected():
    controller, backend, detector, *_ = make_controller(running=False)

    payload = disconnect_command(controller)

    assert payload["error"]["code"] == "not_connected"
    assert backend.stop_calls == []


def test_disconnect_success_processo_separado_sem_pid_em_memoria():
    # Simula um `disconnect` rodando num processo diferente do que originou o
    # `connect` (GUI, ou outra invocação de CLI): a sessão é reconstruída via
    # initialize() sem PID em memória — deve cair no fallback já existente
    # (pkill por nome, aqui representado por stop(None)) sem lançar exceção.
    sessao_previa = ConnectionSession(profile="matriz.conf", iface="tun0", started_at=100.0)
    controller, backend, detector, *_ = make_controller(
        running=True, iface="tun0", active_session=sessao_previa
    )

    payload = disconnect_command(controller)

    assert "error" not in payload
    assert payload["state"] == "disconnected"
    assert backend.stop_calls == [None]
