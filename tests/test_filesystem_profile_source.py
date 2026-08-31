import os

from services.filesystem_profile_source import FilesystemProfileSource


def _make(tmp_path, admin_dir=None, user_dir=None):
    return FilesystemProfileSource(
        admin_dir=str(admin_dir) if admin_dir is not None else str(tmp_path / "admin"),
        user_dir=str(user_dir) if user_dir is not None else str(tmp_path / "user"),
    )


def test_lista_apenas_config_e_conf_ordenados(tmp_path):
    admin = tmp_path / "admin"
    admin.mkdir()
    (admin / "config").write_text("a")
    (admin / "matriz.conf").write_text("b")
    (admin / "filial.conf").write_text("c")
    (admin / "readme.txt").write_text("irrelevante")

    source = _make(tmp_path, admin_dir=admin)

    assert source.list_profiles() == ["config", "filial.conf", "matriz.conf"]


def test_ignora_diretorios_com_nome_valido(tmp_path):
    admin = tmp_path / "admin"
    admin.mkdir()
    (admin / "config").write_text("a")
    (admin / "fake.conf").mkdir()

    source = _make(tmp_path, admin_dir=admin)

    assert source.list_profiles() == ["config"]


def test_diretorio_inexistente_retorna_lista_vazia(tmp_path):
    source = _make(tmp_path, admin_dir=tmp_path / "nao-existe")

    assert source.list_profiles() == []


def test_mescla_perfis_admin_e_usuario(tmp_path):
    admin = tmp_path / "admin"
    user = tmp_path / "user"
    admin.mkdir()
    user.mkdir()
    (admin / "matriz.conf").write_text("admin")
    (user / "pessoal.conf").write_text("usuario")

    source = _make(tmp_path, admin_dir=admin, user_dir=user)

    assert source.list_profiles() == ["matriz.conf", "pessoal.conf"]


def test_colisao_de_nome_prioriza_perfil_admin(tmp_path):
    admin = tmp_path / "admin"
    user = tmp_path / "user"
    admin.mkdir()
    user.mkdir()
    (admin / "matriz.conf").write_text("admin")
    (user / "matriz.conf").write_text("usuario")

    source = _make(tmp_path, admin_dir=admin, user_dir=user)

    assert source.list_profiles() == ["matriz.conf"]
    assert source.resolve_path("matriz.conf") == os.path.join(str(admin), "matriz.conf")


def test_resolve_path_perfil_de_usuario(tmp_path):
    admin = tmp_path / "admin"
    user = tmp_path / "user"
    admin.mkdir()
    user.mkdir()
    (user / "pessoal.conf").write_text("usuario")

    source = _make(tmp_path, admin_dir=admin, user_dir=user)

    assert source.resolve_path("pessoal.conf") == os.path.join(str(user), "pessoal.conf")


def test_resolve_path_perfil_inexistente_cai_no_admin_dir(tmp_path):
    admin = tmp_path / "admin"
    source = _make(tmp_path, admin_dir=admin)

    assert source.resolve_path("fantasma.conf") == os.path.join(str(admin), "fantasma.conf")
