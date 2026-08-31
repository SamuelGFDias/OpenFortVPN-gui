from abc import ABC, abstractmethod


class ProfileSource(ABC):
    @abstractmethod
    def list_profiles(self) -> list[str]: ...

    @abstractmethod
    def resolve_path(self, name: str) -> str: ...

    @abstractmethod
    def is_user_profile(self, name: str) -> bool: ...
