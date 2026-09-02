# Implementation Plan: Interface CLI Programática

**Branch**: `001-add-cli-interface` | **Date**: 2026-09-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-add-cli-interface/spec.md`

## Summary

Expor três subcomandos (`status`, `connect <perfil>`, `disconnect`) no entrypoint já existente
(`openfortivpn-gui`), reaproveitando literalmente o mesmo `VpnController` e os mesmos `services/`
já usados pela GUI (`OpenfortivpnBackend`, `SysfsTunnelDetector`, `FilesystemProfileSource`,
`JsonAppStateStore`, `JsonHistoryStore`), sem duplicar regra de negócio. O entrypoint ganha um
dispatch de argumentos (`argparse`) que decide, antes de importar `ui.application` (e portanto
antes de puxar GTK), se a invocação é modo GUI (comportamento atual, inalterado) ou modo CLI —
para o modo CLI funcionar sem display gráfico. `status --json` expõe estado/perfil/sessão com
campos estruturados estáveis em inglês/snake_case e uma mensagem legível opcional em PT-BR (ver
Clarifications da spec). `connect` bloqueia até confirmar a conexão via polling de `tick()` (mesmo
mecanismo que a GUI já usa, só que síncrono) com timeout; `disconnect` reaproveita o fallback
"matar por nome" já existente para funcionar entre processos diferentes.

## Technical Context

**Language/Version**: Python 3 — mesma versão já usada pelo restante do projeto, sem pin explícito
de versão (shebang `#!/usr/bin/env python3`, sem `pyproject.toml`/`setup.py`).

**Primary Dependencies**: Nenhuma dependência nova. `argparse` (stdlib) para parsing de
subcomandos — já usado como precedente em `dev/render_smoke.py`. Reaproveita integralmente
`controller.vpn_controller.VpnController` e as 5 classes concretas de `services/` já existentes.
GTK/PyGObject/AppIndicator3 continuam usados apenas por `ui/` — o caminho de execução do modo CLI
MUST NOT importar `gi`/`Gtk` em nenhum momento.

**Storage**: Nenhuma nova. Reaproveita os arquivos JSON já existentes
(`~/.config/openfortivpn-gui/state.json`, `$XDG_RUNTIME_DIR/openfortivpn-gui/active_session.json`)
via `JsonAppStateStore`, já resolvidos por `services/runtime_paths.py`.

**Testing**: `pytest`, seguindo o padrão já estabelecido em `tests/test_vpn_controller.py`
(`make_controller()` com fakes dos contratos ABC) — os novos módulos de CLI são testados via fakes,
nunca contra o `openfortivpn` real nem contra GTK.

**Target Platform**: Linux desktop, mesmo ambiente da GUI (a CLI roda no mesmo host, mesmo usuário
do sistema operacional).

**Project Type**: Extensão de aplicação desktop single-project existente — não é um novo projeto
nem uma nova stack; é um novo modo de invocação do mesmo entrypoint.

**Performance Goals**: Sem meta formal de throughput (uso pessoal, invocação sob demanda por
script). `connect` deve confirmar a subida da conexão (ou falhar) dentro de um timeout padrão
curto, coerente com o intervalo de verificação de 1s que a GUI já usa internamente via `tick()`
(ver Phase 0 / research.md para o valor exato escolhido).

**Constraints**: Sem novas dependências de `pip`; modo CLI MUST NOT depender de display gráfico
(`DISPLAY`/Xvfb) para funcionar; `sudo -n` não interativo (Princípio II da constitution) —
`connect`/`disconnect` MUST NOT bloquear esperando senha; CLI MUST NOT escrever fora dos diretórios
já definidos (`~/.config/openfortivpn-gui/`, `$XDG_RUNTIME_DIR/openfortivpn-gui/`).

**Scale/Scope**: Uso pessoal, single-machine, single-user — sem requisito de concorrência
coordenada entre múltiplos consumidores (ver Assumptions da spec).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação |
|---|---|
| I. Camadas Desacopladas via Contratos ABC | **PASS** — a CLI só instancia `VpnController` + as 5 classes concretas de `services/`, exatamente como `ui/application.py` já faz; nenhum código novo de CLI importa `gi`/`Gtk`. |
| II. Sudo Não-Interativo, Nunca Pede Senha | **PASS** — reaproveita `OpenfortivpnBackend`, que já usa `sudo -n` e stdin fechado; nenhum comportamento novo de autenticação é introduzido. |
| III. Perfis Administrados Somente-Leitura | **PASS** (N/A direto) — a CLI apenas consulta e referencia perfis existentes (`FilesystemProfileSource`); não escreve, edita nem cria perfis (fora de escopo, conforme Assumptions da spec). |
| IV. Interface em Português (PT-BR) | **PASS** — resolvido na clarificação da spec: mensagens legíveis para humano em PT-BR; estado/código estruturado em inglês/snake_case (não é "mensagem de UI para usuário final", é contrato de dados para consumidor programático). |
| V. Testes por Contrato, Não por Framework de UI | **PASS** — novos módulos de CLI (dispatch, comandos) MUST ter cobertura via `pytest` com fakes dos contratos ABC, seguindo o padrão de `tests/test_vpn_controller.py`; nenhum teste depende de GTK ou display. |
| VI. Sem Build Step | **PASS** — nenhuma etapa de build/empacotamento introduzida; `argparse` é stdlib, dispatch acontece no mesmo shebang já existente. |

Nenhuma violação — tabela de Complexity Tracking não se aplica.

**Re-check pós-Phase 1 (design)**: `data-model.md`, `contracts/status-schema.json` e
`contracts/cli-commands.md` foram revisados contra os 6 princípios — nenhuma violação nova. Em
particular, `error.code` (inglês/snake_case) + `error.message` (PT-BR) em `ErrorPayload` confirma
a leitura já registrada para o Princípio IV, e nenhum contrato exige tocar em `ui/`, `controller/`
ou `services/` além de extrair o wiring já existente para `cli/wiring.py` (Princípio I).

## Project Structure

### Documentation (this feature)

```text
specs/001-add-cli-interface/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
openfortivpn-gui              # entrypoint existente — ganha dispatch argparse (modo CLI vs GUI)

cli/                           # NOVO pacote
├── __init__.py
├── dispatch.py                # parse de argv (subparsers status/connect/disconnect), decide CLI vs GUI
├── wiring.py                  # monta VpnController + services/ concretos, idêntico a ui/application.py:38-48, sem GTK
├── commands.py                # implementação dos 3 subcomandos sobre o VpnController já montado
└── formatting.py               # serialização de status/erro para --json (payload estruturado) e para texto humano PT-BR

controller/                    # existente, reaproveitado sem alteração de comportamento
services/                      # existente, reaproveitado sem alteração de comportamento
core/                          # existente, reaproveitado sem alteração de comportamento
ui/                             # existente, inalterado — continua o único pacote que importa gi/Gtk

tests/
├── test_cli_dispatch.py        # NOVO — parsing de argv, decisão CLI vs GUI
├── test_cli_commands.py        # NOVO — status/connect/disconnect via fakes dos contratos ABC
└── test_cli_formatting.py      # NOVO — payload --json (schema estável) e mensagem humana PT-BR
```

**Structure Decision**: projeto único existente (não é uma aplicação web nem mobile) — a CLI é um
novo pacote (`cli/`) no mesmo nível de `controller/`, `services/`, `ui/`, seguindo a mesma
convenção de camadas já estabelecida no `AGENTS.md`. `dispatch.py` é o único ponto que decide entre
modo CLI e modo GUI, mantendo `openfortivpn-gui` (entrypoint) como um shim fino, igual já é hoje.

## Complexity Tracking

*Não aplicável — nenhuma violação de Constitution Check.*
