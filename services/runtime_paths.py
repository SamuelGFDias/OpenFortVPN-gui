import os


def resolve_runtime_dir(app_name: str = "openfortivpn-gui") -> str:
    base = os.environ.get("XDG_RUNTIME_DIR") or os.path.expanduser("~/.cache")
    path = os.path.join(base, app_name)
    os.makedirs(path, mode=0o700, exist_ok=True)
    os.chmod(path, 0o700)
    return path


def resolve_user_profile_dir(app_name: str = "openfortivpn-gui") -> str:
    return os.path.expanduser(f"~/.config/{app_name}/profiles")
