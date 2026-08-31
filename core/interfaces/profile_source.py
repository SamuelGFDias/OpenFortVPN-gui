from abc import ABC, abstractmethod


class ProfileSource(ABC):
    @abstractmethod
    def list_profiles(self) -> list[str]: ...
