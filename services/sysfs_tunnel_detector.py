import os

from core.interfaces.tunnel_state_detector import TunnelStateDetector

_PREFIXES = ("ppp", "tun")


class SysfsTunnelDetector(TunnelStateDetector):
    def __init__(self, net_dir: str = "/sys/class/net") -> None:
        self._net_dir = net_dir

    def _current_interfaces(self) -> frozenset[str]:
        try:
            entries = os.listdir(self._net_dir)
        except OSError:
            return frozenset()
        return frozenset(name for name in entries if name.startswith(_PREFIXES))

    def snapshot(self) -> frozenset[str]:
        return self._current_interfaces()

    def detect_new_interface(self, baseline: frozenset[str]) -> str | None:
        # Paridade com o comportamento legado (tunnel_iface()): NÃO diferencia do baseline.
        # Bug conhecido (issue #1) — corrigido na próxima fase.
        current = self._current_interfaces()
        return next(iter(current), None)

    def is_interface_present(self, name: str) -> bool:
        return os.path.exists(os.path.join(self._net_dir, name))
