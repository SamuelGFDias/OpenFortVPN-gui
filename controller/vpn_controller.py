import os
import time

from core.interfaces.profile_source import ProfileSource
from core.interfaces.state_store import AppStateStore, HistoryStore
from core.interfaces.tunnel_state_detector import TunnelStateDetector
from core.interfaces.vpn_backend import VpnBackend
from core.models.connection_session import ConnectionSession
from core.models.connection_state import ConnectionState
from core.models.controller_event import ControllerEvent
from core.models.history_record import HistoryRecord

STOP_GRACE_SECONDS = 3.0


class VpnController:
    def __init__(
        self,
        backend: VpnBackend,
        detector: TunnelStateDetector,
        profile_source: ProfileSource,
        app_state_store: AppStateStore,
        history_store: HistoryStore,
        profile_dir: str = "/etc/openfortivpn",
    ) -> None:
        self._backend = backend
        self._detector = detector
        self._profile_source = profile_source
        self._app_state_store = app_state_store
        self._history_store = history_store
        self._profile_dir = profile_dir

        self._profiles = self._profile_source.list_profiles()
        last = self._app_state_store.load_last_profile()
        self._selected_profile = (
            last if last in self._profiles else (self._profiles[0] if self._profiles else None)
        )

        self._state = ConnectionState.DISCONNECTED
        self._session: ConnectionSession | None = None
        self._stopping_until = 0.0
        self._pending_baseline: frozenset[str] = frozenset()

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def session(self) -> ConnectionSession | None:
        return self._session

    @property
    def profiles(self) -> list[str]:
        return self._profiles

    @property
    def selected_profile(self) -> str | None:
        return self._selected_profile

    def history(self) -> list[HistoryRecord]:
        return self._history_store.load()

    def select_profile(self, name: str) -> None:
        if name in self._profiles and name != self._selected_profile:
            self._selected_profile = name
            self._app_state_store.save_last_profile(name)

    def initialize(self) -> list[ControllerEvent]:
        if self._backend.is_running(None):
            loaded = self._app_state_store.load_active_session()
            iface: str | None = None
            if loaded is not None and loaded.iface and self._detector.is_interface_present(loaded.iface):
                iface = loaded.iface
            else:
                current = self._detector.snapshot()
                iface = next(iter(current), None)
            if iface:
                started_at = loaded.started_at if loaded and loaded.started_at else time.time()
                profile = self._selected_profile or (loaded.profile if loaded else "?")
                self._session = ConnectionSession(profile=profile, iface=iface, started_at=started_at)
                self._state = ConnectionState.CONNECTED
            else:
                self._state = ConnectionState.CONNECTING
                self._session = None
        return []

    def start_connection(self) -> list[ControllerEvent]:
        if not self._selected_profile:
            return [ControllerEvent(kind="connect_failed", reason="Nenhum perfil de VPN configurado")]
        self._app_state_store.save_last_profile(self._selected_profile)
        self._pending_baseline = self._detector.snapshot()
        profile_path = os.path.join(self._profile_dir, self._selected_profile)
        pid = self._backend.start(profile_path)
        self._session = ConnectionSession(profile=self._selected_profile, pid=pid)
        self._state = ConnectionState.CONNECTING
        return []

    def stop_connection(self) -> list[ControllerEvent]:
        session = self._session
        pid = session.pid if session else None
        self._backend.stop(pid)

        events: list[ControllerEvent] = []
        if session is not None and session.started_at is not None:
            end = time.time()
            record = HistoryRecord(profile=session.profile, start=session.started_at, end=end)
            self._history_store.append(record)
            events.append(ControllerEvent(kind="disconnected", duration_seconds=record.duration))
        else:
            events.append(ControllerEvent(kind="cancelled"))

        self._session = None
        self._pending_baseline = frozenset()
        self._state = ConnectionState.DISCONNECTED
        self._stopping_until = time.time() + STOP_GRACE_SECONDS
        self._app_state_store.clear_active_session()
        return events

    def tick(self) -> list[ControllerEvent]:
        events: list[ControllerEvent] = []
        now = time.time()
        if now < self._stopping_until:
            return events

        new_profiles = self._profile_source.list_profiles()
        if new_profiles != self._profiles:
            self._profiles = new_profiles
            if self._selected_profile not in self._profiles:
                self._selected_profile = self._profiles[0] if self._profiles else None
            events.append(ControllerEvent(kind="profiles_changed"))

        pid = self._session.pid if self._session else None
        running = self._backend.is_running(pid)

        if self._state == ConnectionState.CONNECTED and self._session and self._session.iface:
            iface = (
                self._session.iface
                if self._detector.is_interface_present(self._session.iface)
                else None
            )
        else:
            iface = self._detector.detect_new_interface(self._pending_baseline)

        if not running:
            if self._state == ConnectionState.CONNECTED and self._session:
                end = time.time()
                started = self._session.started_at or end
                record = HistoryRecord(profile=self._session.profile, start=started, end=end)
                self._history_store.append(record)
                events.append(ControllerEvent(kind="disconnected", duration_seconds=record.duration))
            elif self._state == ConnectionState.CONNECTING:
                outcome = self._backend.poll_outcome(pid) if pid else None
                events.append(
                    ControllerEvent(kind="connect_failed", reason=outcome.message if outcome else None)
                )
            self._session = None
            self._pending_baseline = frozenset()
            self._state = ConnectionState.DISCONNECTED
            self._app_state_store.clear_active_session()
        elif iface:
            if self._state != ConnectionState.CONNECTED:
                started_at = time.time()
                profile = self._session.profile if self._session else (self._selected_profile or "?")
                new_pid = self._session.pid if self._session else None
                self._session = ConnectionSession(
                    profile=profile, pid=new_pid, iface=iface, started_at=started_at
                )
                self._app_state_store.save_active_session(self._session)
                events.append(ControllerEvent(kind="connected"))
            elif self._session is not None and self._session.iface != iface:
                self._session.iface = iface
            self._state = ConnectionState.CONNECTED
        else:
            self._state = ConnectionState.CONNECTING

        return events
