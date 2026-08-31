from abc import ABC, abstractmethod

from core.models.connection_session import ConnectionSession
from core.models.history_record import HistoryRecord


class AppStateStore(ABC):
    @abstractmethod
    def load_last_profile(self) -> str | None: ...

    @abstractmethod
    def save_last_profile(self, profile: str) -> None: ...

    @abstractmethod
    def load_active_session(self) -> ConnectionSession | None: ...

    @abstractmethod
    def save_active_session(self, session: ConnectionSession) -> None: ...

    @abstractmethod
    def clear_active_session(self) -> None: ...


class HistoryStore(ABC):
    @abstractmethod
    def load(self) -> list[HistoryRecord]: ...

    @abstractmethod
    def append(self, record: HistoryRecord) -> None: ...
