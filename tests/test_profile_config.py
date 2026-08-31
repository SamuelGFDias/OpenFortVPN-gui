from services.profile_config import (
    build_profile_config,
    parse_profile_config,
    sanitize_profile_filename,
    validate_new_profile,
)


def test_sanitize_profile_filename_adiciona_extensao_conf():
    assert sanitize_profile_filename("casa") == "casa.conf"


def test_sanitize_profile_filename_preserva_extensao_existente():
    assert sanitize_profile_filename("casa.conf") == "casa.conf"


def test_sanitize_profile_filename_remove_espacos_nas_pontas():
    assert sanitize_profile_filename("  casa  ") == "casa.conf"


def test_validate_new_profile_ok():
    assert validate_new_profile("casa", "vpn.example.com", "443") is None


def test_validate_new_profile_nome_vazio():
    assert validate_new_profile("", "vpn.example.com", "443") is not None


def test_validate_new_profile_nome_com_caracteres_invalidos():
    assert validate_new_profile("casa/perfil", "vpn.example.com", "443") is not None


def test_validate_new_profile_host_vazio():
    assert validate_new_profile("casa", "", "443") is not None


def test_validate_new_profile_porta_nao_numerica():
    assert validate_new_profile("casa", "vpn.example.com", "abc") is not None


def test_validate_new_profile_porta_vazia_e_permitida():
    assert validate_new_profile("casa", "vpn.example.com", "") is None


def test_validate_new_profile_nome_duplicado():
    error = validate_new_profile("casa", "vpn.example.com", "443", existing_profiles=["casa.conf"])
    assert error is not None


def test_validate_new_profile_nome_nao_duplicado_ok():
    error = validate_new_profile("casa", "vpn.example.com", "443", existing_profiles=["outro.conf"])
    assert error is None


def test_validate_new_profile_editando_o_proprio_nome_nao_conta_como_duplicado():
    error = validate_new_profile(
        "casa", "vpn.example.com", "443", existing_profiles=["casa.conf"], editing_name="casa.conf"
    )
    assert error is None


def test_build_profile_config_campos_completos():
    content = build_profile_config(
        host="vpn.example.com", port="443", username="samuel", password="segredo"
    )

    assert content == (
        "host = vpn.example.com\n"
        "port = 443\n"
        "username = samuel\n"
        "password = segredo\n"
    )


def test_build_profile_config_porta_vazia_usa_443():
    content = build_profile_config(host="vpn.example.com", port="", username="", password="")

    assert content == "host = vpn.example.com\nport = 443\n"


def test_build_profile_config_omite_username_e_password_vazios():
    content = build_profile_config(host="vpn.example.com", port="8443", username="", password="")

    assert content == "host = vpn.example.com\nport = 8443\n"


def test_build_profile_config_preserva_campos_extras_desconhecidos():
    content = build_profile_config(
        host="vpn.example.com",
        port="443",
        username="samuel",
        password="",
        extra={"trusted-cert": "abc123", "host": "ignorado"},
    )

    assert content == "host = vpn.example.com\nport = 443\nusername = samuel\ntrusted-cert = abc123\n"


def test_parse_profile_config_extrai_pares_chave_valor():
    content = "host = vpn.example.com\nport = 443\nusername = samuel\n"

    assert parse_profile_config(content) == {
        "host": "vpn.example.com",
        "port": "443",
        "username": "samuel",
    }


def test_parse_profile_config_ignora_comentarios_e_linhas_vazias():
    content = "# comentário\nhost = vpn.example.com\n\nport = 443\n"

    assert parse_profile_config(content) == {"host": "vpn.example.com", "port": "443"}


def test_parse_profile_config_e_build_profile_config_fazem_round_trip_de_campos_extras():
    original = "host = vpn.example.com\nport = 443\ntrusted-cert = abc123\n"
    fields = parse_profile_config(original)

    rebuilt = build_profile_config(
        host=fields["host"], port=fields["port"], username="", password="", extra=fields
    )

    assert rebuilt == "host = vpn.example.com\nport = 443\ntrusted-cert = abc123\n"
