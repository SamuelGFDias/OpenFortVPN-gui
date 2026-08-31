import os

from core.interfaces.profile_source import ProfileSource


class FilesystemProfileSource(ProfileSource):
    def __init__(self, profile_dir: str = "/etc/openfortivpn") -> None:
        self._profile_dir = profile_dir

    def list_profiles(self) -> list[str]:
        try:
            entries = os.listdir(self._profile_dir)
        except OSError:
            return []
        names = []
        for entry in sorted(entries):
            if entry == "config" or entry.endswith(".conf"):
                path = os.path.join(self._profile_dir, entry)
                if os.path.isfile(path):
                    names.append(entry)
        return names
