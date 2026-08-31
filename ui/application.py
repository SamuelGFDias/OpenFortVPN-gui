import subprocess

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
gi.require_version("AppIndicator3", "0.1")
from gi.repository import Gdk, GLib, Gtk

from controller.vpn_controller import VpnController
from core.models.connection_state import ConnectionState
from core.models.controller_event import ControllerEvent
from services.filesystem_profile_source import FilesystemProfileSource
from services.json_state_store import JsonAppStateStore, JsonHistoryStore
from services.openfortivpn_backend import OpenfortivpnBackend
from services.sysfs_tunnel_detector import SysfsTunnelDetector
from ui.connect_page import CSS, ConnectPage
from ui.formatting import fmt
from ui.history_page import HistoryPage
from ui.tray_indicator import TrayIndicator

ICON_ON = "network-vpn"
ICON_OFF = "network-offline"


class VpnApp(Gtk.Application):
    def __init__(self, application_id: str = "local.openfortivpn.gui") -> None:
        super().__init__(application_id=application_id)

        self._controller = VpnController(
            backend=OpenfortivpnBackend(),
            detector=SysfsTunnelDetector(),
            profile_source=FilesystemProfileSource(),
            app_state_store=JsonAppStateStore(),
            history_store=JsonHistoryStore(),
        )

        self.win: Gtk.ApplicationWindow | None = None
        self._connect_page: ConnectPage | None = None
        self._history_page: HistoryPage | None = None
        self._tray: TrayIndicator | None = None

    def do_activate(self) -> None:
        if self.win is not None:
            self.win.present()
            return

        self._apply_css()

        self.win = Gtk.ApplicationWindow(application=self)
        self.win.set_title("OpenFortiVPN")
        self.win.set_default_size(400, 480)
        self.win.connect("delete-event", self.on_delete)

        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        self.win.set_titlebar(hb)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.set_margin_top(12)
        root.set_margin_bottom(12)
        root.set_margin_start(12)
        root.set_margin_end(12)
        self.win.add(root)

        stack = Gtk.Stack()
        stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        stack.set_transition_duration(200)

        switcher = Gtk.StackSwitcher()
        switcher.set_stack(stack)
        switcher.set_halign(Gtk.Align.CENTER)
        root.pack_start(switcher, False, False, 0)
        root.pack_start(stack, True, True, 0)

        self._connect_page = ConnectPage(
            profiles=self._controller.profiles,
            selected_profile=self._controller.selected_profile,
            on_profile_selected=self._on_profile_selected,
            on_button_clicked=self._on_button_clicked,
        )
        self._history_page = HistoryPage()

        stack.add_titled(self._connect_page.widget, "connect", "Conexão")
        stack.add_titled(self._history_page.widget, "history", "Histórico")

        self._tray = TrayIndicator(
            profiles=self._controller.profiles,
            selected_profile=self._controller.selected_profile,
            on_toggle=self._on_button_clicked,
            on_show=self.show_win,
            on_quit=self.on_quit,
            on_profile_selected=self._on_profile_selected,
        )

        events = self._controller.initialize()
        self._handle_events(events)

        self._refresh_history()
        self._render()
        self.win.show_all()
        GLib.timeout_add_seconds(1, self._tick)

    def _apply_css(self) -> None:
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def show_win(self) -> None:
        if self.win is not None:
            self.win.present()

    def on_delete(self, _w: Gtk.Widget, _e: Gdk.Event) -> bool:
        self.win.hide()
        return True

    def on_quit(self) -> None:
        if self._controller.session is not None:
            self._handle_events(self._controller.stop_connection())
        self.quit()

    def _on_profile_selected(self, name: str) -> None:
        self._controller.select_profile(name)
        self._render()

    def _on_button_clicked(self) -> None:
        if self._controller.state in (ConnectionState.CONNECTING, ConnectionState.CONNECTED):
            events = self._controller.stop_connection()
        else:
            events = self._controller.start_connection()
        self._handle_events(events)
        self._render()

    def _tick(self) -> bool:
        events = self._controller.tick()
        self._handle_events(events)
        self._render()
        return True

    def _handle_events(self, events: list[ControllerEvent]) -> None:
        for event in events:
            if event.kind == "connected":
                self._notify("Conectado à VPN", ICON_ON)
            elif event.kind == "disconnected":
                self._notify(
                    f"Desconectado — tempo de conexão: {fmt(event.duration_seconds or 0)}",
                    ICON_OFF,
                )
                self._refresh_history()
            elif event.kind == "cancelled":
                self._notify("Cancelado", ICON_OFF)
            elif event.kind == "connect_failed":
                if event.reason is None:
                    self._notify("Falha ao conectar", "dialog-error")
                else:
                    self._notify(f"Falha ao conectar — {event.reason}", "dialog-error")

    def _notify(self, msg: str, icon: str = ICON_ON) -> None:
        subprocess.Popen(
            ["notify-send", "-i", icon, "OpenFortiVPN", msg],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _refresh_history(self) -> None:
        if self._history_page is not None:
            self._history_page.refresh(self._controller.history())

    def _render(self) -> None:
        session = self._controller.session
        elapsed_text = ""
        if session is not None and session.started_at is not None:
            elapsed_text = fmt(session.elapsed_seconds())

        if self._connect_page is not None:
            self._connect_page.set_selected_profile(self._controller.selected_profile)
            self._connect_page.render(
                state=self._controller.state,
                elapsed_text=elapsed_text,
                has_profiles=bool(self._controller.profiles),
            )

        if self._tray is not None:
            self._tray.set_selected_profile(self._controller.selected_profile)
            self._tray.render(state=self._controller.state, elapsed_text=elapsed_text)


if __name__ == "__main__":
    app = VpnApp()
    app.run(None)
