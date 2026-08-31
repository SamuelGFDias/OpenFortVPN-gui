from controller.vpn_controller import VpnController
from core.interfaces.profile_source import ProfileSource
from core.interfaces.state_store import AppStateStore, HistoryStore
from core.interfaces.tunnel_state_detector import TunnelStateDetector
from core.interfaces.vpn_backend import VpnBackend
from core.models.connect_outcome import ConnectOutcome
from core.models.connection_session import ConnectionSession
from core.models.connection_state import ConnectionState


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
        # Conjunto opcional de interfaces "presentes" independente de `iface`,
        # usado para testar is_interface_present() de forma desacoplada do
        # valor único de `iface` (ex.: reattach onde a iface salva difere da
        # que o snapshot "cru" traria).
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


def test_fluxo_disconnected_para_connecting_para_connected():
    controller, backend, detector, app_state_store, history_store = make_controller()

    assert controller.state == ConnectionState.DISCONNECTED

    events = controller.start_connection()
    assert events == []
    assert controller.state == ConnectionState.CONNECTING
    assert backend.start_calls == ["/etc/openfortivpn/matriz.conf"]

    # tick sem interface ainda: continua conectando
    events = controller.tick()
    assert controller.state == ConnectionState.CONNECTING
    assert events == []

    # interface aparece: transiciona para conectado
    detector.iface = "tun0"
    events = controller.tick()
    assert controller.state == ConnectionState.CONNECTED
    assert len(events) == 1
    assert events[0].kind == "connected"
    assert controller.session is not None
    assert controller.session.iface == "tun0"
    assert app_state_store.saved_sessions  # sessão ativa persistida


def test_stop_connection_registra_historico_corretamente():
    controller, backend, detector, app_state_store, history_store = make_controller()

    controller.start_connection()
    detector.iface = "tun0"
    controller.tick()
    assert controller.state == ConnectionState.CONNECTED

    events = controller.stop_connection()

    assert len(events) == 1
    assert events[0].kind == "disconnected"
    assert len(history_store.records) == 1
    assert history_store.records[0].profile == "matriz.conf"
    assert controller.state == ConnectionState.DISCONNECTED
    assert controller.session is None
    assert app_state_store.cleared == 1
    assert backend.stop_calls == [100]


def test_stop_connection_sem_sessao_com_started_at_emite_cancelled():
    controller, backend, detector, app_state_store, history_store = make_controller()

    controller.start_connection()
    # ainda conectando (sem started_at) quando cancela
    events = controller.stop_connection()

    assert len(events) == 1
    assert events[0].kind == "cancelled"
    assert history_store.records == []


def test_tick_detecta_queda_externa_do_processo_e_registra_historico():
    controller, backend, detector, app_state_store, history_store = make_controller()

    controller.start_connection()
    detector.iface = "tun0"
    controller.tick()
    assert controller.state == ConnectionState.CONNECTED

    # processo cai sozinho, sem stop_connection() explícito
    backend.running = False
    events = controller.tick()

    assert len(events) == 1
    assert events[0].kind == "disconnected"
    assert len(history_store.records) == 1
    assert controller.state == ConnectionState.DISCONNECTED
    assert controller.session is None
    assert app_state_store.cleared == 1


def test_tick_falha_ao_conectar_quando_processo_cai_durante_connecting():
    controller, backend, detector, app_state_store, history_store = make_controller()

    controller.start_connection()
    # processo nunca chega a rodar / cai antes de estabelecer túnel
    backend.running = False

    events = controller.tick()

    assert len(events) == 1
    assert events[0].kind == "connect_failed"
    assert controller.state == ConnectionState.DISCONNECTED
    assert history_store.records == []


def test_initialize_com_sessao_ja_ativa_reattach():
    sessao_previa = ConnectionSession(profile="matriz.conf", started_at=500.0)
    controller, backend, detector, app_state_store, history_store = make_controller(
        running=True, iface="tun0", active_session=sessao_previa
    )

    events = controller.initialize()

    assert events == []
    assert controller.state == ConnectionState.CONNECTED
    assert controller.session is not None
    assert controller.session.iface == "tun0"
    assert controller.session.started_at == 500.0


def test_initialize_processo_rodando_sem_interface_fica_connecting():
    controller, backend, detector, app_state_store, history_store = make_controller(
        running=True, iface=None
    )

    controller.initialize()

    assert controller.state == ConnectionState.CONNECTING
    assert controller.session is None


def test_initialize_sem_processo_rodando_mantem_disconnected():
    controller, backend, detector, app_state_store, history_store = make_controller(running=False)

    controller.initialize()

    assert controller.state == ConnectionState.DISCONNECTED


def test_start_connection_sem_perfil_configurado_retorna_connect_failed():
    controller, backend, detector, app_state_store, history_store = make_controller(profiles=())

    assert controller.selected_profile is None

    events = controller.start_connection()

    assert len(events) == 1
    assert events[0].kind == "connect_failed"
    assert events[0].reason == "Nenhum perfil de VPN configurado"
    assert backend.start_calls == []
    assert controller.state == ConnectionState.DISCONNECTED


def test_select_profile_atualiza_selecionado_e_persiste():
    controller, backend, detector, app_state_store, history_store = make_controller(
        profiles=("a.conf", "b.conf")
    )

    controller.select_profile("b.conf")

    assert controller.selected_profile == "b.conf"
    assert app_state_store.load_last_profile() == "b.conf"


def test_select_profile_com_nome_invalido_e_ignorado():
    controller, backend, detector, app_state_store, history_store = make_controller(
        profiles=("a.conf",), last_profile="a.conf"
    )

    controller.select_profile("inexistente.conf")

    assert controller.selected_profile == "a.conf"


def test_interface_preexistente_antes_de_start_nao_dispara_connected_sozinha():
    controller, backend, detector, app_state_store, history_store = make_controller()

    # tun0 já existe no sistema antes de start_connection() ser chamado.
    detector.iface = "tun0"

    controller.start_connection()
    assert controller.state == ConnectionState.CONNECTING

    # tick imediatamente após: só a interface pré-existente (no baseline)
    # está presente — não deve, sozinha, disparar "connected" (issue #1).
    events = controller.tick()
    assert controller.state == ConnectionState.CONNECTING
    assert events == []

    # uma interface nova (fora do baseline) aparece: agora sim conecta.
    detector.iface = "tun1"
    events = controller.tick()

    assert controller.state == ConnectionState.CONNECTED
    assert len(events) == 1
    assert events[0].kind == "connected"
    assert controller.session.iface == "tun1"


def test_initialize_reattach_prioriza_iface_salva_sobre_snapshot_cru():
    sessao_previa = ConnectionSession(profile="filial.conf", iface="tun5", started_at=300.0)
    controller, backend, detector, app_state_store, history_store = make_controller(
        running=True, profiles=("filial.conf",), active_session=sessao_previa
    )
    # A iface salva ("tun5") está presente, mas o snapshot "cru" do detector
    # traria outra interface ("tun9") caso o controller ignorasse a sessão
    # salva e caísse direto no fallback "qualquer interface presente".
    detector.iface = "tun9"
    detector._present = {"tun5", "tun9"}

    events = controller.initialize()

    assert events == []
    assert controller.state == ConnectionState.CONNECTED
    assert controller.session is not None
    assert controller.session.iface == "tun5"
    assert controller.session.started_at == 300.0


def test_initialize_reattach_sem_sessao_salva_usa_qualquer_interface_presente():
    controller, backend, detector, app_state_store, history_store = make_controller(
        running=True, iface="tun0", active_session=None
    )

    events = controller.initialize()

    assert events == []
    assert controller.state == ConnectionState.CONNECTED
    assert controller.session is not None
    assert controller.session.iface == "tun0"
