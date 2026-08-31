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
from services.filesystem_profile_writer import FilesystemProfileWriter
from services.filesystem_theme_provider import DEFAULT_THEME_NAME, FilesystemThemeProvider
from services.json_profile_icon_store import JsonProfileIconStore
from services.json_state_store import JsonAppStateStore, JsonHistoryStore
from services.json_theme_settings_store import JsonThemeSettingsStore
from services.openfortivpn_backend import OpenfortivpnBackend
from services.profile_config import (
    build_profile_config,
    parse_profile_config,
    sanitize_profile_filename,
    validate_new_profile,
)
from services.sysfs_tunnel_detector import SysfsTunnelDetector
from ui.connect_page import ConnectPage
from ui.formatting import fmt
from ui.history_page import HistoryPage
from ui.profile_dialog import ProfileDialog
from ui.tray_indicator import TrayIndicator

ICON_ON = "network-vpn"
ICON_OFF = "network-offline"


class VpnApp(Gtk.Application):
    def __init__(self, application_id: str = "local.openfortivpn.gui") -> None:
        super().__init__(application_id=application_id)

        self._profile_source = FilesystemProfileSource()
        self._controller = VpnController(
            backend=OpenfortivpnBackend(),
            detector=SysfsTunnelDetector(),
            profile_source=self._profile_source,
            app_state_store=JsonAppStateStore(),
            history_store=JsonHistoryStore(),
        )

        self._theme_provider = FilesystemThemeProvider()
        self._theme_settings = JsonThemeSettingsStore()
        self._css_provider: Gtk.CssProvider | None = None
        self._current_theme: str = DEFAULT_THEME_NAME

        self._profile_writer = FilesystemProfileWriter()
        self._profile_icon_store = JsonProfileIconStore()
        self._profile_icons: dict[str, str] = {}

        self.win: Gtk.ApplicationWindow | None = None
        self._connect_page: ConnectPage | None = None
        self._history_page: HistoryPage | None = None
        self._tray: TrayIndicator | None = None

    def do_activate(self) -> None:
        if self.win is not None:
            self.win.present()
            return

        self._apply_theme(self._theme_settings.load_selected_theme() or DEFAULT_THEME_NAME)

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
        self._stack = stack

        switcher = Gtk.StackSwitcher()
        switcher.set_stack(stack)
        switcher.set_halign(Gtk.Align.CENTER)
        root.pack_start(switcher, False, False, 0)
        root.pack_start(stack, True, True, 0)

        self._profile_icons = self._profile_icon_store.load_all()

        self._connect_page = ConnectPage(
            profiles=self._controller.profiles,
            selected_profile=self._controller.selected_profile,
            profile_icons=self._profile_icons,
            on_profile_selected=self._on_profile_selected,
            on_button_clicked=self._on_button_clicked,
            on_new_profile=self._on_new_profile_requested,
            on_edit_profile=self._on_edit_profile_requested,
        )
        self._history_page = HistoryPage()

        stack.add_titled(self._connect_page.widget, "connect", "Conexão")
        stack.add_titled(self._history_page.widget, "history", "Histórico")

        self._tray = TrayIndicator(
            profiles=self._controller.profiles,
            selected_profile=self._controller.selected_profile,
            profile_icons=self._profile_icons,
            on_toggle=self._on_button_clicked,
            on_show=self.show_win,
            on_quit=self.on_quit,
            on_profile_selected=self._on_profile_selected,
            on_new_profile=self._on_new_profile_requested,
            on_edit_profile=self._on_edit_profile_requested,
            themes=self._theme_provider.list_themes(),
            selected_theme=self._current_theme,
            on_theme_selected=self._on_theme_selected,
        )

        events = self._controller.initialize()
        self._handle_events(events)

        self._refresh_history()
        self._render()
        self.win.show_all()
        GLib.timeout_add_seconds(1, self._tick)

    def _resolve_css(self, name: str) -> bytes:
        try:
            return self._theme_provider.load_css(name)
        except (FileNotFoundError, OSError):
            if name != DEFAULT_THEME_NAME:
                try:
                    return self._theme_provider.load_css(DEFAULT_THEME_NAME)
                except (FileNotFoundError, OSError):
                    pass
            return b""

    def _apply_theme(self, name: str) -> None:
        css_bytes = self._resolve_css(name)
        if self._css_provider is None:
            self._css_provider = Gtk.CssProvider()
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(),
                self._css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
        self._css_provider.load_from_data(css_bytes)
        self._current_theme = name

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

    def _on_theme_selected(self, name: str) -> None:
        self._apply_theme(name)
        self._theme_settings.save_selected_theme(name)

    def _on_new_profile_requested(self) -> None:
        dialog = ProfileDialog(self.win)
        try:
            while True:
                response = dialog.run()
                if response != Gtk.ResponseType.OK:
                    return
                values = dialog.get_values()
                error = validate_new_profile(
                    values["name"], values["host"], values["port"], self._controller.profiles
                )
                if error:
                    dialog.show_error(error)
                    continue

                filename = sanitize_profile_filename(values["name"])
                content = build_profile_config(
                    host=values["host"],
                    port=values["port"],
                    username=values["username"],
                    password=values["password"],
                )
                self._profile_writer.save_profile(filename, content)
                if values["icon"]:
                    self._profile_icon_store.save_icon(filename, values["icon"])
                self._profile_icons = self._profile_icon_store.load_all()

                self._handle_events(self._controller.refresh_profiles())
                self._controller.select_profile(filename)
                self._render()
                return
        finally:
            dialog.destroy()

    def _on_edit_profile_requested(self) -> None:
        name = self._controller.selected_profile
        if not name:
            return
        if not self._profile_source.is_user_profile(name):
            self._notify(
                "Perfil administrado pelo sistema — não pode ser editado pela GUI",
                "dialog-information",
            )
            return

        path = self._profile_source.resolve_path(name)
        try:
            with open(path) as f:
                content = f.read()
        except OSError:
            content = ""
        fields = parse_profile_config(content)

        existing = {
            "name": name,
            "host": fields.get("host", ""),
            "port": fields.get("port", ""),
            "username": fields.get("username", ""),
            "password": fields.get("password", ""),
            "icon": self._profile_icons.get(name),
        }

        dialog = ProfileDialog(self.win, existing=existing)
        try:
            while True:
                response = dialog.run()
                if response != Gtk.ResponseType.OK:
                    return
                values = dialog.get_values()
                error = validate_new_profile(
                    values["name"],
                    values["host"],
                    values["port"],
                    self._controller.profiles,
                    editing_name=name,
                )
                if error:
                    dialog.show_error(error)
                    continue

                content = build_profile_config(
                    host=values["host"],
                    port=values["port"],
                    username=values["username"],
                    password=values["password"],
                    extra=fields,
                )
                self._profile_writer.save_profile(name, content)
                if values["icon"]:
                    self._profile_icon_store.save_icon(name, values["icon"])
                    self._profile_icons = self._profile_icon_store.load_all()
                    # Nome do perfil não muda ao editar — sem evento "profiles_changed" — mas
                    # o ícone pode ter mudado: repopula os widgets para refleti-lo.
                    if self._connect_page is not None:
                        self._connect_page.set_profiles(
                            self._controller.profiles, self._controller.selected_profile, self._profile_icons
                        )
                    if self._tray is not None:
                        self._tray.set_profiles(
                            self._controller.profiles, self._controller.selected_profile, self._profile_icons
                        )
                self._render()
                return
        finally:
            dialog.destroy()

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
            elif event.kind == "profiles_changed":
                if self._connect_page is not None:
                    self._connect_page.set_profiles(
                        self._controller.profiles, self._controller.selected_profile, self._profile_icons
                    )
                if self._tray is not None:
                    self._tray.set_profiles(
                        self._controller.profiles, self._controller.selected_profile, self._profile_icons
                    )

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
