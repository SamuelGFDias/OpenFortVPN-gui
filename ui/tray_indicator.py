from typing import Callable

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
    ) -> None:
        self._profiles = list(profiles)
        self._selected_profile = selected_profile
        self._on_toggle = on_toggle
        self._on_show = on_show
        self._on_quit = on_quit
        self._on_profile_selected = on_profile_selected

        self.menu_status = Gtk.MenuItem()
        self.menu_time = Gtk.MenuItem()
        self.menu_status.set_sensitive(False)
        self.menu_time.set_sensitive(False)

        prof_menu = Gtk.Menu()
        group: list[Gtk.RadioMenuItem] = []
        for name in self._profiles:
            item = Gtk.RadioMenuItem.new_with_label(group, name)
            group = item.get_group()
            item.connect("activate", self._on_profile_item, name)
            if name == self._selected_profile:
                item.set_active(True)
            prof_menu.append(item)
        self.prof_parent = Gtk.MenuItem(f"VPN: {self._selected_profile or '-'}")
        self.prof_parent.set_submenu(prof_menu)

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

    def _on_profile_item(self, _item: Gtk.RadioMenuItem, name: str) -> None:
        if name != self._selected_profile:
            self._selected_profile = name
            self._on_profile_selected(name)

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
