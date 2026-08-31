import time

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from core.models.history_record import HistoryRecord
from ui.formatting import fmt


class HistoryPage:
    def __init__(self) -> None:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(12)
        box.set_margin_end(12)

        self._store = Gtk.ListStore(str, str, str)
        tree = Gtk.TreeView(model=self._store)
        tree.set_headers_visible(True)
        for title, idx in (("Início", 0), ("VPN", 1), ("Duração", 2)):
            col = Gtk.TreeViewColumn(title, Gtk.CellRendererText(), text=idx)
            col.set_expand(idx == 0)
            tree.append_column(col)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(260)
        scrolled.add(tree)
        box.pack_start(scrolled, True, True, 0)

        self.widget = box

    def refresh(self, records: list[HistoryRecord]) -> None:
        self._store.clear()
        for r in sorted(records, key=lambda r: r.start, reverse=True):
            start_s = time.strftime("%d/%m %H:%M", time.localtime(r.start))
            self._store.append([start_s, r.profile or "?", fmt(r.duration)])
