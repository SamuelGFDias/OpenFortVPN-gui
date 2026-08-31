from services.json_profile_icon_store import JsonProfileIconStore


def test_save_icon_round_trip(tmp_path):
    store = JsonProfileIconStore(store_path=str(tmp_path / "profile_icons.json"))

    store.save_icon("casa.conf", "/home/user/icons/casa.png")

    assert store.load_all() == {"casa.conf": "/home/user/icons/casa.png"}


def test_load_all_retorna_vazio_se_arquivo_nao_existe(tmp_path):
    store = JsonProfileIconStore(store_path=str(tmp_path / "nao_existe.json"))

    assert store.load_all() == {}


def test_save_icon_preserva_entradas_existentes(tmp_path):
    store = JsonProfileIconStore(store_path=str(tmp_path / "profile_icons.json"))

    store.save_icon("casa.conf", "network-vpn")
    store.save_icon("trabalho.conf", "/tmp/trabalho.png")

    assert store.load_all() == {
        "casa.conf": "network-vpn",
        "trabalho.conf": "/tmp/trabalho.png",
    }


def test_load_all_ignora_entradas_com_tipo_invalido(tmp_path):
    path = tmp_path / "profile_icons.json"
    path.write_text('{"casa.conf": "network-vpn", "invalido": 42}')
    store = JsonProfileIconStore(store_path=str(path))

    assert store.load_all() == {"casa.conf": "network-vpn"}
