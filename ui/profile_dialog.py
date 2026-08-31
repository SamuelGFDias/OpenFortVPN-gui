import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class ProfileDialog(Gtk.Dialog):
    def __init__(self, parent: Gtk.Window | None, existing: dict | None = None) -> None:
        title = "Editar perfil VPN" if existing else "Novo perfil VPN"
        super().__init__(title=title, transient_for=parent)
        self.set_modal(True)
        self.add_buttons(
            "Cancelar", Gtk.ResponseType.CANCEL,
            "Salvar", Gtk.ResponseType.OK,
        )
        self.set_default_response(Gtk.ResponseType.OK)

        grid = Gtk.Grid(row_spacing=8, column_spacing=8)
        grid.set_margin_top(12)
        grid.set_margin_bottom(12)
        grid.set_margin_start(12)
        grid.set_margin_end(12)

        self.name_entry = Gtk.Entry()
        self.host_entry = Gtk.Entry()
        self.port_entry = Gtk.Entry()
        self.port_entry.set_text("443")
        self.username_entry = Gtk.Entry()
        self.password_entry = Gtk.Entry()
        self.password_entry.set_visibility(False)

        self.icon_chooser = Gtk.FileChooserButton(title="Escolher ícone (opcional)")
        img_filter = Gtk.FileFilter()
        img_filter.set_name("Imagens")
        img_filter.add_mime_type("image/*")
        self.icon_chooser.add_filter(img_filter)

        if existing:
            # Editar não permite renomear (evita ter que mover arquivo, atualizar
            # último perfil selecionado, histórico etc. — fora do escopo da issue #7).
            self.name_entry.set_text(existing.get("name", ""))
            self.name_entry.set_sensitive(False)
            self.host_entry.set_text(existing.get("host", ""))
            self.port_entry.set_text(existing.get("port") or "443")
            self.username_entry.set_text(existing.get("username", ""))
            self.password_entry.set_text(existing.get("password", ""))
            icon = existing.get("icon")
            if icon and icon.startswith("/"):
                self.icon_chooser.set_filename(icon)

        rows = [
            ("Nome do perfil:", self.name_entry),
            ("Host:", self.host_entry),
            ("Porta:", self.port_entry),
            ("Usuário:", self.username_entry),
            ("Senha:", self.password_entry),
            ("Ícone (opcional):", self.icon_chooser),
        ]
        for i, (label_text, widget) in enumerate(rows):
            label = Gtk.Label(label=label_text)
            label.set_halign(Gtk.Align.END)
            grid.attach(label, 0, i, 1, 1)
            widget.set_hexpand(True)
            grid.attach(widget, 1, i, 1, 1)

        self.error_label = Gtk.Label()
        self.error_label.set_halign(Gtk.Align.START)
        self.error_label.set_line_wrap(True)
        self.error_label.set_visible(False)
        grid.attach(self.error_label, 0, len(rows), 2, 1)

        content = self.get_content_area()
        content.add(grid)
        self.show_all()
        self.error_label.set_visible(False)

    def get_values(self) -> dict:
        return {
            "name": self.name_entry.get_text(),
            "host": self.host_entry.get_text(),
            "port": self.port_entry.get_text(),
            "username": self.username_entry.get_text(),
            "password": self.password_entry.get_text(),
            "icon": self.icon_chooser.get_filename(),
        }

    def show_error(self, message: str) -> None:
        self.error_label.set_text(f"⚠ {message}")
        self.error_label.set_visible(True)
