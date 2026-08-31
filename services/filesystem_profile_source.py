import os

from core.interfaces.profile_source import ProfileSource
from services.runtime_paths import resolve_user_profile_dir


class FilesystemProfileSource(ProfileSource):
    def __init__(self, admin_dir: str = "/etc/openfortivpn", user_dir: str | None = None) -> None:
        self._admin_dir = admin_dir
        self._user_dir = user_dir or resolve_user_profile_dir()

    def list_profiles(self) -> list[str]:
        names: set[str] = set()
        for base_dir in (self._admin_dir, self._user_dir):
            names.update(self._list_dir(base_dir))
        return sorted(names)

    def resolve_path(self, name: str) -> str:
        # Perfis administrados (/etc/openfortivpn) têm prioridade em caso de
        # colisão de nome com um perfil criado pela GUI.
        for base_dir in (self._admin_dir, self._user_dir):
            path = os.path.join(base_dir, name)
            if os.path.isfile(path):
                return path
        return os.path.join(self._admin_dir, name)

    def is_user_profile(self, name: str) -> bool:
        # Só perfis em ~/.config/openfortivpn-gui/profiles/ são editáveis pela GUI —
        # /etc/openfortivpn/ é administrado fora dela (issue #7).
        return os.path.isfile(os.path.join(self._user_dir, name))

    def _list_dir(self, base_dir: str) -> list[str]:
        try:
            entries = os.listdir(base_dir)
        except OSError:
            return []
        names = []
        for entry in entries:
            if entry == "config" or entry.endswith(".conf"):
                path = os.path.join(base_dir, entry)
                if os.path.isfile(path):
                    names.append(entry)
        return names
