import pytest

from services.filesystem_theme_provider import FilesystemThemeProvider


def test_list_themes_retorna_uniao_ordenada_dos_dois_diretorios(tmp_path):
    builtin_dir = tmp_path / "builtin"
    user_dir = tmp_path / "user"
    builtin_dir.mkdir()
    user_dir.mkdir()
    (builtin_dir / "default.css").write_text("a")
    (builtin_dir / "dark.css").write_text("b")
    (user_dir / "custom.css").write_text("c")

    provider = FilesystemThemeProvider(builtin_dir=str(builtin_dir), user_dir=str(user_dir))

    assert provider.list_themes() == ["custom", "dark", "default"]


def test_load_css_le_conteudo_correto(tmp_path):
    builtin_dir = tmp_path / "builtin"
    user_dir = tmp_path / "user"
    builtin_dir.mkdir()
    user_dir.mkdir()
    (builtin_dir / "default.css").write_bytes(b"body { color: red; }")

    provider = FilesystemThemeProvider(builtin_dir=str(builtin_dir), user_dir=str(user_dir))

    assert provider.load_css("default") == b"body { color: red; }"


def test_load_css_prioriza_user_dir_quando_mesmo_nome(tmp_path):
    builtin_dir = tmp_path / "builtin"
    user_dir = tmp_path / "user"
    builtin_dir.mkdir()
    user_dir.mkdir()
    (builtin_dir / "default.css").write_bytes(b"builtin")
    (user_dir / "default.css").write_bytes(b"user")

    provider = FilesystemThemeProvider(builtin_dir=str(builtin_dir), user_dir=str(user_dir))

    assert provider.load_css("default") == b"user"


def test_load_css_nome_inexistente_levanta_file_not_found(tmp_path):
    builtin_dir = tmp_path / "builtin"
    user_dir = tmp_path / "user"
    builtin_dir.mkdir()
    user_dir.mkdir()

    provider = FilesystemThemeProvider(builtin_dir=str(builtin_dir), user_dir=str(user_dir))

    with pytest.raises(FileNotFoundError):
        provider.load_css("inexistente")
