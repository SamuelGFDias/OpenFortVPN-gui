import os

from core.interfaces.theme_settings_store import ThemeSettingsStore
from services.json_utils import load_json, save_json


class JsonThemeSettingsStore(ThemeSettingsStore):
    def __init__(
        self,
        settings_path: str = os.path.expanduser("~/.config/openfortivpn-gui/theme.json"),
    ) -> None:
        self._settings_path = settings_path

    def load_selected_theme(self) -> str | None:
        data = load_json(self._settings_path, {})
        if not isinstance(data, dict):
            return None
        return data.get("selected_theme")

    def save_selected_theme(self, name: str) -> None:
        data = load_json(self._settings_path, {})
        if not isinstance(data, dict):
            data = {}
        data["selected_theme"] = name
        save_json(self._settings_path, data)
