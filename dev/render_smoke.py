#!/usr/bin/env python3
"""Renderiza a janela principal da GUI sob um display X (real ou Xvfb) e salva um
screenshot em PNG, para inspeção visual do layout/CSS sem precisar de display físico.

Não conecta nenhuma VPN de verdade — só ativa a janela e captura a imagem. Requer que
DISPLAY já esteja apontando para um servidor X válido (ver dev/render_smoke.sh).

Uso:
    python3 dev/render_smoke.py [saida.png] [--page connect|history] [--delay SEGUNDOS]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("AppIndicator3", "0.1")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from ui.application import VpnApp  # noqa: E402


def _capture(win: Gtk.Window, output: str) -> None:
    gdk_window = win.get_window()
    width, height = win.get_size()
    pixbuf = Gdk.pixbuf_get_from_window(gdk_window, 0, 0, width, height)
    if pixbuf is None:
        raise RuntimeError("Não foi possível capturar o conteúdo da janela (pixbuf None)")
    pixbuf.savev(output, "png", [], [])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", default="/tmp/openfortivpn-gui-render.png")
    parser.add_argument("--page", choices=["connect", "history"], default="connect")
    parser.add_argument("--delay", type=float, default=1.5, help="segundos antes do screenshot")
    args = parser.parse_args()

    app = VpnApp(application_id="local.openfortivpn.gui.dev")
    result = {"ok": False, "error": None}

    def on_activated(app: VpnApp) -> None:
        def snap() -> bool:
            try:
                if app.win is None:
                    raise RuntimeError("janela não foi criada por do_activate()")
                stack = getattr(app, "_stack", None)
                if args.page == "history" and stack is not None:
                    stack.set_visible_child_name("history")
                    # dá um tempo extra pro Gtk.Stack terminar a transição de página
                    while Gtk.events_pending():
                        Gtk.main_iteration()
                _capture(app.win, args.output)
                result["ok"] = True
            except Exception as exc:  # noqa: BLE001 - queremos reportar qualquer falha
                result["error"] = str(exc)
            finally:
                app.quit()
            return False

        GLib.timeout_add(int(args.delay * 1000), snap)

    app.connect_after("activate", on_activated)
    app.run(None)

    if not result["ok"]:
        print(f"FALHA: {result['error']}", file=sys.stderr)
        return 1
    print(f"Screenshot salvo em {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
