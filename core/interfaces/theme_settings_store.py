from abc import ABC, abstractmethod


class ThemeSettingsStore(ABC):
    @abstractmethod
    def load_selected_theme(self) -> str | None: ...

    @abstractmethod
    def save_selected_theme(self, name: str) -> None: ...
