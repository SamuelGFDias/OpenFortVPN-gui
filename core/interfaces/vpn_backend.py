from abc import ABC, abstractmethod

from core.models.connect_outcome import ConnectOutcome


class VpnBackend(ABC):
    @abstractmethod
    def start(self, profile_path: str) -> int:
        """Lança o túnel desacoplado da GUI. Retorna o PID do processo lançado."""

    @abstractmethod
    def stop(self, pid: int | None) -> None:
        """Encerra a sessão. Se pid é None, degrada para busca por nome de processo."""

    @abstractmethod
    def is_running(self, pid: int | None) -> bool: ...

    @abstractmethod
    def poll_outcome(self, pid: int) -> ConnectOutcome | None:
        """Não bloqueante. Retorna o desfecho se o processo já terminou, senão None."""
