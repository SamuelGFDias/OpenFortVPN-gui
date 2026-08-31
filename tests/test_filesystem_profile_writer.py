import os
import stat

from services.filesystem_profile_writer import FilesystemProfileWriter


def test_save_profile_cria_arquivo_com_conteudo(tmp_path):
    writer = FilesystemProfileWriter(profile_dir=str(tmp_path / "profiles"))

    path = writer.save_profile("casa.conf", "host = vpn.example.com\nport = 443\n")

    assert os.path.isfile(path)
    assert open(path).read() == "host = vpn.example.com\nport = 443\n"


def test_save_profile_cria_diretorio_e_arquivo_com_permissoes_restritas(tmp_path):
    profile_dir = tmp_path / "profiles"
    writer = FilesystemProfileWriter(profile_dir=str(profile_dir))

    path = writer.save_profile("casa.conf", "host = vpn.example.com\n")

    dir_mode = stat.S_IMODE(os.stat(profile_dir).st_mode)
    file_mode = stat.S_IMODE(os.stat(path).st_mode)
    assert dir_mode == 0o700
    assert file_mode == 0o600


def test_save_profile_sobrescreve_arquivo_existente(tmp_path):
    writer = FilesystemProfileWriter(profile_dir=str(tmp_path / "profiles"))

    writer.save_profile("casa.conf", "host = old\n")
    path = writer.save_profile("casa.conf", "host = new\n")

    assert open(path).read() == "host = new\n"
