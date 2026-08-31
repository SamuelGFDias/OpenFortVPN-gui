from abc import ABC, abstractmethod


class ThemeProvider(ABC):
    @abstractmethod
    def list_themes(self) -> list[str]:
        """Nomes dos temas disponíveis (sem a extensão .css), embutidos + do usuário."""

    @abstractmethod
    def load_css(self, name: str) -> bytes:
        """Conteúdo CSS do tema. Levanta FileNotFoundError se o nome não existir."""
