import os

from core.interfaces.theme_provider import ThemeProvider

DEFAULT_THEME_NAME = "default"
_BUILTIN_THEMES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui", "themes"
)


class FilesystemThemeProvider(ThemeProvider):
    def __init__(
        self,
        builtin_dir: str = _BUILTIN_THEMES_DIR,
        user_dir: str | None = None,
    ) -> None:
        self._builtin_dir = builtin_dir
        self._user_dir = user_dir or os.path.expanduser("~/.config/openfortivpn-gui/themes")

    def list_themes(self) -> list[str]:
        names: set[str] = set()
        for directory in (self._builtin_dir, self._user_dir):
            try:
                entries = os.listdir(directory)
            except OSError:
                continue
            for entry in entries:
                if entry.endswith(".css") and os.path.isfile(os.path.join(directory, entry)):
                    names.add(entry[: -len(".css")])
        return sorted(names)

    def load_css(self, name: str) -> bytes:
        # Tema do usuário tem prioridade sobre o embutido em caso de nome igual.
        for directory in (self._user_dir, self._builtin_dir):
            path = os.path.join(directory, f"{name}.css")
            if os.path.isfile(path):
                with open(path, "rb") as f:
                    return f.read()
        raise FileNotFoundError(f"Tema '{name}' não encontrado")
