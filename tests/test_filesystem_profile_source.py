from services.filesystem_profile_source import FilesystemProfileSource


def test_lista_apenas_config_e_conf_ordenados(tmp_path):
    (tmp_path / "config").write_text("a")
    (tmp_path / "matriz.conf").write_text("b")
    (tmp_path / "filial.conf").write_text("c")
    (tmp_path / "readme.txt").write_text("irrelevante")

    source = FilesystemProfileSource(profile_dir=str(tmp_path))

    assert source.list_profiles() == ["config", "filial.conf", "matriz.conf"]


def test_ignora_diretorios_com_nome_valido(tmp_path):
    (tmp_path / "config").write_text("a")
    (tmp_path / "fake.conf").mkdir()

    source = FilesystemProfileSource(profile_dir=str(tmp_path))

    assert source.list_profiles() == ["config"]


def test_diretorio_inexistente_retorna_lista_vazia(tmp_path):
    source = FilesystemProfileSource(profile_dir=str(tmp_path / "nao-existe"))

    assert source.list_profiles() == []
