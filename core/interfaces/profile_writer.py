from abc import ABC, abstractmethod


class ProfileWriter(ABC):
    @abstractmethod
    def save_profile(self, name: str, content: str) -> str: ...
