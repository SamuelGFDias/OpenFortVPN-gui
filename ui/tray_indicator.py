from typing import Callable

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("AppIndicator3", "0.1")
from gi.repository import AppIndicator3, Gtk

from core.models.connection_state import ConnectionState

ICON_ON = "network-vpn"
ICON_OFF = "network-offline"


class TrayIndicator:
    def __init__(
        self,
        profiles: list[str],
        selected_profile: str | None,
        on_toggle: Callable[[], None],
        on_show: Callable[[], None],
        on_quit: Callable[[], None],
        on_profile_selected: Callable[[str], None],
        themes: list[str] | None = None,
        selected_theme: str | None = None,
        on_theme_selected: Callable[[str], None] | None = None,
    ) -> None:
        self._profiles = list(profiles)
        self._selected_profile = selected_profile
        self._on_toggle = on_toggle
        self._on_show = on_show
        self._on_quit = on_quit
        self._on_profile_selected = on_profile_selected
        self._themes = list(themes or [])
        self._selected_theme = selected_theme
        self._on_theme_selected = on_theme_selected

        self.menu_status = Gtk.MenuItem()
        self.menu_time = Gtk.MenuItem()
        self.menu_status.set_sensitive(False)
        self.menu_time.set_sensitive(False)

        self.prof_parent = Gtk.MenuItem(f"VPN: {self._selected_profile or '-'}")
        self.prof_parent.set_submenu(self._build_profile_submenu())

        self.theme_parent = Gtk.MenuItem(f"Tema: {self._selected_theme or '-'}")
        self.theme_parent.set_submenu(self._build_theme_submenu())

        self.menu_toggle = Gtk.MenuItem("Ligar VPN")
        self.menu_toggle.connect("activate", lambda *a: self._on_toggle())

        menu_show = Gtk.MenuItem("Mostrar janela")
        menu_show.connect("activate", lambda *a: self._on_show())

        menu_quit = Gtk.MenuItem("Sair")
        menu_quit.connect("activate", lambda *a: self._on_quit())

        menu = Gtk.Menu()
        menu.append(self.menu_status)
        menu.append(self.menu_time)
        menu.append(Gtk.SeparatorMenuItem())
        menu.append(self.prof_parent)
        menu.append(self.theme_parent)
        menu.append(self.menu_toggle)
        menu.append(menu_show)
        menu.append(Gtk.SeparatorMenuItem())
        menu.append(menu_quit)
        menu.show_all()

        self.ind = AppIndicator3.Indicator.new(
            "openfortivpn-tray",
            ICON_OFF,
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
        )
        self.ind.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.ind.set_menu(menu)
        self.ind.set_title("OpenFortiVPN")

    def _build_profile_submenu(self) -> Gtk.Menu:
        prof_menu = Gtk.Menu()
        group: list[Gtk.RadioMenuItem] = []
        for name in self._profiles:
            item = Gtk.RadioMenuItem.new_with_label(group, name)
            group = item.get_group()
            item.connect("activate", self._on_profile_item, name)
            if name == self._selected_profile:
                item.set_active(True)
            prof_menu.append(item)
        prof_menu.show_all()
        return prof_menu

    def _on_profile_item(self, _item: Gtk.RadioMenuItem, name: str) -> None:
        if name != self._selected_profile:
            self._selected_profile = name
            self._on_profile_selected(name)

    def set_profiles(self, profiles: list[str], selected_profile: str | None) -> None:
        # Gtk.RadioMenuItem não tem "remover todos": reconstrói o submenu
        # inteiro sempre que a lista de perfis muda em runtime (issue #6).
        self._profiles = list(profiles)
        self._selected_profile = selected_profile
        self.prof_parent.set_submenu(self._build_profile_submenu())
        self.prof_parent.set_label(f"VPN: {self._selected_profile or '-'}")

    def _build_theme_submenu(self) -> Gtk.Menu:
        theme_menu = Gtk.Menu()
        group: list[Gtk.RadioMenuItem] = []
        for name in self._themes:
            item = Gtk.RadioMenuItem.new_with_label(group, name)
            group = item.get_group()
            item.connect("activate", self._on_theme_item, name)
            if name == self._selected_theme:
                item.set_active(True)
            theme_menu.append(item)
        theme_menu.show_all()
        return theme_menu

    def _on_theme_item(self, _item: Gtk.RadioMenuItem, name: str) -> None:
        if name != self._selected_theme and self._on_theme_selected is not None:
            self._selected_theme = name
            self._on_theme_selected(name)

    def set_themes(self, themes: list[str], selected_theme: str | None) -> None:
        self._themes = list(themes)
        self._selected_theme = selected_theme
        self.theme_parent.set_submenu(self._build_theme_submenu())
        self.theme_parent.set_label(f"Tema: {self._selected_theme or '-'}")

    def set_selected_profile(self, name: str | None) -> None:
        # Igual ao update_tray_profile() legado: só atualiza o texto do submenu,
        # sem reconstruir os radio items.
        self._selected_profile = name
        if self.prof_parent:
            self.prof_parent.set_label(f"VPN: {name or '-'}")

    def render(self, *, state: ConnectionState, elapsed_text: str) -> None:
        if state == ConnectionState.CONNECTING:
            self.menu_status.set_label("Status: Conectando…")
            self.menu_time.set_label("Estabelecendo túnel…")
            self.menu_toggle.set_label("Cancelar")
            self.ind.set_icon(ICON_ON)
        elif state == ConnectionState.CONNECTED:
            self.menu_status.set_label("Status: Conectado")
            self.menu_time.set_label(f"Tempo: {elapsed_text}")
            self.menu_toggle.set_label("Desligar VPN")
            self.ind.set_icon(ICON_ON)
        else:
            self.menu_status.set_label("Status: Desconectado")
            self.menu_time.set_label(" ")
            self.menu_toggle.set_label("Ligar VPN")
            self.ind.set_icon(ICON_OFF)
