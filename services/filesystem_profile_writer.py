import os

from core.interfaces.profile_writer import ProfileWriter
from services.runtime_paths import resolve_user_profile_dir


class FilesystemProfileWriter(ProfileWriter):
    # Só escreve no diretório de perfis do usuário — nunca em /etc/openfortivpn,
    # que permanece somente-leitura e administrado fora da GUI (issue #7).
    def __init__(self, profile_dir: str | None = None) -> None:
        self._profile_dir = profile_dir or resolve_user_profile_dir()

    def save_profile(self, name: str, content: str) -> str:
        os.makedirs(self._profile_dir, mode=0o700, exist_ok=True)
        os.chmod(self._profile_dir, 0o700)
        path = os.path.join(self._profile_dir, name)
        with open(path, "w") as f:
            f.write(content)
        os.chmod(path, 0o600)
        return path
