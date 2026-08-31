import os
import stat

from services.runtime_paths import resolve_runtime_dir


def _mode(path: str) -> int:
    return stat.S_IMODE(os.stat(path).st_mode)


def test_usa_xdg_runtime_dir_quando_definido(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))

    resolved = resolve_runtime_dir()

    assert resolved == str(tmp_path / "openfortivpn-gui")
    assert os.path.isdir(resolved)
    assert _mode(resolved) == 0o700


def test_cai_para_home_cache_quando_xdg_runtime_dir_ausente(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    resolved = resolve_runtime_dir()

    assert resolved == str(tmp_path / ".cache" / "openfortivpn-gui")
    assert os.path.isdir(resolved)
    assert _mode(resolved) == 0o700
