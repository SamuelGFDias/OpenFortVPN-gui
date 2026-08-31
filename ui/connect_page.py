from typing import Callable

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from core.models.connection_state import ConnectionState


class ConnectPage:
    def __init__(
        self,
        profiles: list[str],
        selected_profile: str | None,
        on_profile_selected: Callable[[str], None],
        on_button_clicked: Callable[[], None],
    ) -> None:
        self._profiles = list(profiles)
        self._selected_profile = selected_profile
        self._on_profile_selected = on_profile_selected
        self._on_button_clicked = on_button_clicked

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        box.set_margin_start(28)
        box.set_margin_end(28)

        prof_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        prof_lbl = Gtk.Label("VPN:")
        prof_box.pack_start(prof_lbl, False, False, 0)
        self.profile_combo = Gtk.ComboBoxText()
        self.profile_combo.set_name("profile_combo")
        for name in self._profiles:
            self.profile_combo.append_text(name)
        if self._selected_profile and self._selected_profile in self._profiles:
            self.profile_combo.set_active(self._profiles.index(self._selected_profile))
        self.profile_combo.connect("changed", self._on_combo_changed)
        prof_box.pack_start(self.profile_combo, True, True, 0)
        box.pack_start(prof_box, False, False, 0)

        self.status = Gtk.Label(halign=Gtk.Align.CENTER)
        self.status.get_style_context().add_class("status-pill")
        box.pack_start(self.status, False, False, 0)

        self.spinner = Gtk.Spinner()
        self.spinner.set_halign(Gtk.Align.CENTER)
        self.spinner.set_visible(False)
        box.pack_start(self.spinner, False, False, 0)

        self.time_label = Gtk.Label(halign=Gtk.Align.CENTER)
        self.time_label.get_style_context().add_class("dim-label")
        box.pack_start(self.time_label, False, False, 0)

        self.btn = Gtk.Button(label="Ligar VPN")
        self.btn.set_name("connect_button")
        self.btn.set_halign(Gtk.Align.CENTER)
        self.btn.connect("clicked", self._on_clicked)
        box.pack_start(self.btn, False, False, 0)

        self.widget = box

    def _on_combo_changed(self, combo: Gtk.ComboBoxText) -> None:
        name = combo.get_active_text()
        if name and name != self._selected_profile:
            self._selected_profile = name
            self._on_profile_selected(name)

    def _on_clicked(self, _btn: Gtk.Button) -> None:
        self._on_button_clicked()

    def set_profiles(self, profiles: list[str], selected_profile: str | None) -> None:
        # Reconstrói o combo quando a lista de perfis muda em runtime (issue #6).
        # Bloqueia o handler "changed" durante a reconstrução para não disparar
        # on_profile_selected espuriamente ao repopular/selecionar.
        self._profiles = list(profiles)
        self._selected_profile = selected_profile
        self.profile_combo.handler_block_by_func(self._on_combo_changed)
        self.profile_combo.remove_all()
        for name in self._profiles:
            self.profile_combo.append_text(name)
        if self._selected_profile and self._selected_profile in self._profiles:
            self.profile_combo.set_active(self._profiles.index(self._selected_profile))
        self.profile_combo.handler_unblock_by_func(self._on_combo_changed)

    def set_selected_profile(self, name: str | None) -> None:
        # Mantém o combo em sincronia quando a seleção muda por outra via (ex.: tray),
        # sem reemitir on_profile_selected — igual ao efeito do on_profile_item legado.
        self._selected_profile = name
        if name and name in self._profiles:
            self.profile_combo.handler_block_by_func(self._on_combo_changed)
            self.profile_combo.set_active(self._profiles.index(name))
            self.profile_combo.handler_unblock_by_func(self._on_combo_changed)

    def render(
        self,
        *,
        state: ConnectionState,
        elapsed_text: str,
        has_profiles: bool,
    ) -> None:
        idle = state == ConnectionState.DISCONNECTED
        self.profile_combo.set_sensitive(idle and has_profiles)
        if not has_profiles:
            self.btn.set_sensitive(False)

        status_ctx = self.status.get_style_context()
        for cls in ("state-connecting", "state-connected", "state-disconnected"):
            status_ctx.remove_class(cls)

        btn_ctx = self.btn.get_style_context()
        btn_ctx.remove_class("suggested-action")
        btn_ctx.remove_class("destructive-action")

        if state == ConnectionState.CONNECTING:
            self.status.set_text("Conectando…")
            status_ctx.add_class("state-connecting")
            self.time_label.set_text("Estabelecendo túnel…")
            self.btn.set_label("Cancelar")
            btn_ctx.add_class("destructive-action")
            self.spinner.set_visible(True)
            self.spinner.start()
        elif state == ConnectionState.CONNECTED:
            self.status.set_text("Conectado")
            status_ctx.add_class("state-connected")
            self.time_label.set_text(f"Tempo de conexão: {elapsed_text}")
            self.btn.set_label("Desligar VPN")
            btn_ctx.add_class("destructive-action")
            self.spinner.stop()
            self.spinner.set_visible(False)
        else:
            self.status.set_text("Desconectado")
            status_ctx.add_class("state-disconnected")
            self.time_label.set_text(" ")
            self.btn.set_label("Ligar VPN")
            btn_ctx.add_class("suggested-action")
            self.spinner.stop()
            self.spinner.set_visible(False)
