"""Wiring do `VpnController` com as implementações concretas de `services/`.

Compartilhado entre a GUI (`ui/application.py`) e a CLI (`cli/dispatch.py`), para não haver
duas fontes de verdade sobre "como montar o controller" — ver
`specs/001-add-cli-interface/research.md` §2. Não importa `gi`/`Gtk` em nenhum momento, para
que o modo CLI funcione sem display gráfico.
"""

from controller.vpn_controller import VpnController
from services.filesystem_profile_source import FilesystemProfileSource
from services.json_state_store import JsonAppStateStore, JsonHistoryStore
from services.openfortivpn_backend import OpenfortivpnBackend
from services.sysfs_tunnel_detector import SysfsTunnelDetector


def build_controller() -> VpnController:
    return VpnController(
        backend=OpenfortivpnBackend(),
        detector=SysfsTunnelDetector(),
        profile_source=FilesystemProfileSource(),
        app_state_store=JsonAppStateStore(),
        history_store=JsonHistoryStore(),
    )
