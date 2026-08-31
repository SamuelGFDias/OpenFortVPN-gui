import gi

gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, Gtk

DEFAULT_PROFILE_ICON = "network-vpn"


def load_profile_pixbuf(icon_value: str | None, size: int = 16) -> GdkPixbuf.Pixbuf | None:
    for candidate in (icon_value, DEFAULT_PROFILE_ICON):
        if not candidate:
            continue
        pixbuf = _try_load(candidate, size)
        if pixbuf is not None:
            return pixbuf
    return None


def _try_load(value: str, size: int) -> GdkPixbuf.Pixbuf | None:
    try:
        if value.startswith("/"):
            return GdkPixbuf.Pixbuf.new_from_file_at_size(value, size, size)
        return Gtk.IconTheme.get_default().load_icon(value, size, 0)
    except Exception:
        return None
