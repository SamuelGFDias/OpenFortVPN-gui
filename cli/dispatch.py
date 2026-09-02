"""Dispatch de `argv` para os subcomandos da CLI (`status`, `connect`, `disconnect`).

Ver `specs/001-add-cli-interface/contracts/cli-commands.md` para o contrato exato de cada
subcomando e `specs/001-add-cli-interface/research.md` §1 para a decisão de dispatch CLI vs
GUI no entrypoint (`openfortivpn-gui`, raiz). Este módulo não importa `gi`/`Gtk`.
"""

import argparse
import json

from cli import commands, wiring
from cli.formatting import format_human

KNOWN_COMMANDS = frozenset({"status", "connect", "disconnect"})


def is_cli_invocation(argv: list[str]) -> bool:
    """True quando `argv` começa por um subcomando reconhecido da CLI.

    Usado pelo entrypoint para decidir entre modo CLI e modo GUI *antes* de
    `from ui.application import VpnApp` (que puxa GTK) — sem argumentos, ou com um
    argumento não reconhecido, cai no comportamento atual (abre a GUI).
    """
    return bool(argv) and argv[0] in KNOWN_COMMANDS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openfortivpn-gui",
        description="Interface gráfica e CLI para gerenciar túneis openfortivpn.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser(
        "status", help="Consulta o estado atual da conexão VPN"
    )
    status_parser.add_argument(
        "--json", action="store_true", help="Saída em JSON estruturado"
    )

    connect_parser = subparsers.add_parser(
        "connect", help="Conecta a um perfil de VPN, bloqueando até confirmar"
    )
    connect_parser.add_argument("profile", help="Nome do perfil de VPN (não o caminho)")
    connect_parser.add_argument(
        "--json", action="store_true", help="Saída em JSON estruturado"
    )
    connect_parser.add_argument(
        "--timeout",
        type=float,
        default=commands.DEFAULT_CONNECT_TIMEOUT,
        help="Timeout em segundos aguardando a conexão subir (padrão: 20)",
    )

    disconnect_parser = subparsers.add_parser(
        "disconnect", help="Desconecta a conexão VPN ativa"
    )
    disconnect_parser.add_argument(
        "--json", action="store_true", help="Saída em JSON estruturado"
    )

    return parser


def _print_payload(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(format_human(payload))


def main(argv: list[str]) -> int:
    """Ponto de entrada da CLI: faz parse de `argv`, executa o subcomando e devolve o
    exit code (`0` sucesso, `1` falha de domínio, `2` uso inválido — via `argparse`)."""
    parser = build_parser()
    args = parser.parse_args(argv)

    controller = wiring.build_controller()

    if args.command == "status":
        payload = commands.status_command(controller)
        _print_payload(payload, args.json)
        return 0

    if args.command == "connect":
        payload = commands.connect_command(controller, args.profile, timeout=args.timeout)
        _print_payload(payload, args.json)
        return 1 if "error" in payload else 0

    if args.command == "disconnect":
        payload = commands.disconnect_command(controller)
        _print_payload(payload, args.json)
        return 1 if "error" in payload else 0

    parser.error(f"comando desconhecido: {args.command}")  # pragma: no cover
    return 2  # pragma: no cover
