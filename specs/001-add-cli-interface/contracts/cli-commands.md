# Contrato de comandos — `openfortivpn-gui` CLI

## `openfortivpn-gui status [--json]`

Consulta o estado atual, sem efeito colateral.

- **Saída (sucesso, sempre)**: `StatusPayload` — texto humano em PT-BR por padrão, JSON
  (`contracts/status-schema.json`) com `--json`.
- **Exit code**: sempre `0` (é somente leitura — não há caso de falha de negócio; erro de
  infraestrutura inesperado usa `error.code = "internal_error"`, exit `1`).

## `openfortivpn-gui connect <perfil> [--json] [--timeout SEGUNDOS]`

Inicia conexão ao perfil informado; bloqueia até confirmar ou até o timeout.

- **Argumento posicional**: `<perfil>` — nome do perfil (não caminho), conforme já listado em
  `status`/`controller.profiles`.
- **`--timeout SEGUNDOS`** (opcional): sobrescreve o timeout padrão de 20s (ver `research.md` §3).
- **Saída (sucesso)**: `StatusPayload` já refletindo `state: "connected"`. Exit `0`.
- **Saída (falha)**: `ErrorPayload` com um dos códigos: `profile_not_found`, `already_connected`,
  `connect_timeout`, `sudo_denied`, `internal_error`. Exit `1`.

## `openfortivpn-gui disconnect [--json]`

Encerra a conexão ativa, de qualquer origem (GUI ou `connect` via CLI, mesmo em processo
diferente).

- **Saída (sucesso)**: `StatusPayload` já refletindo `state: "disconnected"`. Exit `0`.
- **Saída (falha)**: `ErrorPayload` com um dos códigos: `not_connected`, `sudo_denied`,
  `internal_error`. Exit `1`.

## Convenção de exit code (todos os comandos)

| Exit code | Significado |
|---|---|
| `0` | Sucesso |
| `1` | Falha de domínio — ver `error.code` no payload para o motivo |
| `2` | Uso inválido da CLI (argumento faltando/malformado) — comportamento padrão do `argparse` |

## Compatibilidade com o modo GUI

`openfortivpn-gui` sem argumentos (ou com argumentos não reconhecidos como um dos três subcomandos
acima) continua abrindo a interface gráfica, comportamento idêntico ao anterior a esta feature.
