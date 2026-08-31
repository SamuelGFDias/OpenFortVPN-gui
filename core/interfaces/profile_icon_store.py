from abc import ABC, abstractmethod


class ProfileIconStore(ABC):
    @abstractmethod
    def load_all(self) -> dict[str, str]: ...

    @abstractmethod
    def save_icon(self, profile: str, icon: str) -> None: ...
