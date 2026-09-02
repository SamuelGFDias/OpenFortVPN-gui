import pytest

from cli.dispatch import build_parser, is_cli_invocation, main

# Testa só parsing de argv e a decisão CLI vs GUI (tasks.md T019) — sem tocar no
# controller real (cli.wiring.build_controller() só é chamado depois de um parse bem
# sucedido, o que estes testes evitam deliberadamente).


def test_dispatch_routes_to_cli():
    assert is_cli_invocation(["status"]) is True
    assert is_cli_invocation(["status", "--json"]) is True
    assert is_cli_invocation(["connect", "matriz.conf"]) is True
    assert is_cli_invocation(["connect", "matriz.conf", "--timeout", "5"]) is True
    assert is_cli_invocation(["disconnect"]) is True
    assert is_cli_invocation(["disconnect", "--json"]) is True


def test_dispatch_falls_back_to_gui():
    assert is_cli_invocation([]) is False
    assert is_cli_invocation(["--help"]) is False
    assert is_cli_invocation(["algum-argumento-desconhecido"]) is False


def test_dispatch_invalid_args_exit_code_2():
    with pytest.raises(SystemExit) as exc_info:
        main(["connect"])  # falta o <perfil> posicional obrigatório

    assert exc_info.value.code == 2


def test_dispatch_comando_desconhecido_exit_code_2():
    with pytest.raises(SystemExit) as exc_info:
        main(["voar"])

    assert exc_info.value.code == 2


def test_dispatch_status_subparser_aceita_json_flag():
    parser = build_parser()

    args = parser.parse_args(["status", "--json"])

    assert args.command == "status"
    assert args.json is True


def test_dispatch_status_subparser_json_default_false():
    parser = build_parser()

    args = parser.parse_args(["status"])

    assert args.json is False


def test_dispatch_connect_subparser_perfil_e_timeout_default():
    parser = build_parser()

    args = parser.parse_args(["connect", "matriz.conf"])

    assert args.command == "connect"
    assert args.profile == "matriz.conf"
    assert args.timeout == 20.0
    assert args.json is False


def test_dispatch_connect_subparser_timeout_customizado():
    parser = build_parser()

    args = parser.parse_args(["connect", "matriz.conf", "--timeout", "5"])

    assert args.timeout == 5.0


def test_dispatch_disconnect_subparser():
    parser = build_parser()

    args = parser.parse_args(["disconnect", "--json"])

    assert args.command == "disconnect"
    assert args.json is True
