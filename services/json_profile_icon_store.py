import os

from core.interfaces.profile_icon_store import ProfileIconStore
from services.json_utils import load_json, save_json


class JsonProfileIconStore(ProfileIconStore):
    def __init__(
        self,
        store_path: str = os.path.expanduser("~/.config/openfortivpn-gui/profile_icons.json"),
    ) -> None:
        self._store_path = store_path

    def load_all(self) -> dict[str, str]:
        data = load_json(self._store_path, {})
        if not isinstance(data, dict):
            return {}
        return {k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, str)}

    def save_icon(self, profile: str, icon: str) -> None:
        data = load_json(self._store_path, {})
        if not isinstance(data, dict):
            data = {}
        data[profile] = icon
        save_json(self._store_path, data)
