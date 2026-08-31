from abc import ABC, abstractmethod


class TunnelStateDetector(ABC):
    @abstractmethod
    def snapshot(self) -> frozenset[str]:
        """Interfaces tun*/ppp* existentes agora — baseline tirado antes de iniciar a conexão."""

    @abstractmethod
    def detect_new_interface(self, baseline: frozenset[str]) -> str | None:
        """Interface tun*/ppp* que não estava no baseline, ou None se nenhuma nova apareceu."""

    @abstractmethod
    def is_interface_present(self, name: str) -> bool: ...
