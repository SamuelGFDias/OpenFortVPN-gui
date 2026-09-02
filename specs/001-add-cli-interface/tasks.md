---

description: "Task list template for feature implementation"
---

# Tasks: Interface CLI Programática

**Input**: Design documents from `/specs/001-add-cli-interface/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Incluídas — o Princípio V da constitution exige cobertura via `pytest` com fakes dos
contratos ABC para tudo fora de `ui/`, e o código novo desta feature (`cli/`) é exatamente esse caso.

**Organization**: Tarefas agrupadas por user story (spec.md) para permitir implementação e teste
independentes de cada uma.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: US1 = status, US2 = connect, US3 = disconnect

## Path Conventions

Projeto único existente — `cli/` (novo pacote) e `tests/` na raiz do repositório, conforme
`plan.md` § Project Structure.

---

## Phase 1: Setup

**Purpose**: criar o esqueleto do novo pacote, sem lógica ainda.

- [x] T001 Criar pacote `cli/` com `cli/__init__.py` vazio.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: infraestrutura compartilhada pelas 3 user stories — nenhuma pode ser implementada
antes desta fase.

**⚠️ CRITICAL**: nenhuma user story começa antes desta fase estar completa.

- [x] T002 Extrair o wiring do `VpnController` de `ui/application.py:38-48` para uma função nova
  `build_controller() -> VpnController` em `cli/wiring.py`, instanciando
  `OpenfortivpnBackend()`, `SysfsTunnelDetector()`, `FilesystemProfileSource()`,
  `JsonAppStateStore()`, `JsonHistoryStore()` — literalmente o mesmo código, sem `import gi`/`Gtk`.
- [x] T003 Atualizar `ui/application.py` para chamar `cli.wiring.build_controller()` no lugar do
  wiring inline em `VpnApp.__init__`, preservando exatamente o comportamento atual da GUI
  (nenhuma mudança visível ao usuário).
- [x] T004 [P] Criar `cli/formatting.py` com as funções de serialização do `StatusPayload` e
  `ErrorPayload` (`data-model.md`, `contracts/status-schema.json`): `status_payload(controller) -> dict`,
  `error_payload(code: str, message: str) -> dict`, e `format_human(payload: dict) -> str` (texto
  legível em PT-BR para o modo sem `--json`).
- [x] T005 [P] Criar `cli/dispatch.py` com `argparse.ArgumentParser` e subparsers `status`
  (`--json`), `connect` (`<perfil>`, `--json`, `--timeout SEGUNDOS`) e `disconnect` (`--json`),
  conforme `contracts/cli-commands.md`. `main(argv) -> int` retorna o exit code; ainda sem chamar
  `cli.commands` (placeholders `NotImplementedError` até a Phase 3+).
- [x] T006 Atualizar o entrypoint `openfortivpn-gui` (raiz) para checar se `sys.argv[1:]` casa com
  um subcomando reconhecido por `cli.dispatch` **antes** de `from ui.application import VpnApp`;
  se sim, despacha para `cli.dispatch.main(sys.argv[1:])` e usa o valor de retorno como
  `sys.exit(...)`; caso contrário, mantém o comportamento atual (`VpnApp().run(None)`) sem
  nenhuma mudança de import ordering para esse caminho.

**Checkpoint**: pacote `cli/` existe, wiring compartilhado funciona, dispatch reconhece os 3
subcomandos (mesmo que ainda não façam nada) — user stories podem começar.

---

## Phase 3: User Story 1 - Consultar status da VPN por fora (Priority: P1) 🎯 MVP

**Goal**: `openfortivpn-gui status [--json]` funciona, com ou sem GUI aberta.

**Independent Test**: rodar `status --json` em cada um dos 3 estados (desconectado/conectando/conectado) e validar a saída contra `contracts/status-schema.json`.

### Tests for User Story 1 ⚠️

> Escrever estes testes primeiro; devem falhar antes da implementação.

- [x] T007 [P] [US1] Teste `test_status_disconnected`, `test_status_connected`,
  `test_status_connecting` em `tests/test_cli_commands.py`, usando os mesmos fakes de
  `tests/test_vpn_controller.py` (`FakeVpnBackend`, `FakeTunnelStateDetector`,
  `FakeProfileSource`, `FakeAppStateStore`, `FakeHistoryStore`) injetados num `VpnController` real
  — sem GTK, sem `cli.wiring.build_controller()` (isso é testado à parte, T018).
- [x] T008 [P] [US1] Teste `test_status_payload_schema` e `test_status_human_text` em
  `tests/test_cli_formatting.py`, validando que `status_payload()` produz exatamente os campos de
  `contracts/status-schema.json` (nenhum campo a mais, nenhum a menos — inclusive confirmando que
  `pid` NÃO aparece, conforme `data-model.md`).

### Implementation for User Story 1

- [x] T009 [US1] Implementar `status_command(controller) -> dict` em `cli/commands.py`: chama
  `controller.initialize()` (para refletir o processo real, `research.md` §3/`plan.md`) e retorna
  `formatting.status_payload(controller)`. Sempre sucesso (exit `0`), sem `ErrorPayload`, conforme
  `contracts/cli-commands.md`.
- [x] T010 [US1] Ligar o subcomando `status` em `cli/dispatch.py` a `commands.status_command`,
  formatando a saída via `formatting.format_human`/JSON conforme a flag `--json`, e retornando `0`.

**Checkpoint**: `status --json` funcional e testável isoladamente (MVP entregável).

---

## Phase 4: User Story 2 - Conectar a um perfil por fora (Priority: P2)

**Goal**: `openfortivpn-gui connect <perfil> [--json] [--timeout SEGUNDOS]` funciona, bloqueando até confirmar ou falhar.

**Independent Test**: rodar `connect <perfil-válido>` com a VPN desconectada e confirmar via `status` que subiu; rodar com perfil inexistente e com conexão já ativa e confirmar os `error.code` corretos.

### Tests for User Story 2 ⚠️

- [x] T011 [P] [US2] Teste `test_connect_success`, `test_connect_profile_not_found`,
  `test_connect_already_connected`, `test_connect_timeout` em `tests/test_cli_commands.py`, com um
  fake de `VpnBackend` cujo `is_running`/detector de interface é controlável pelo teste para
  simular subida rápida (sucesso) e subida que nunca completa (timeout) sem esperar 20s de verdade
  (usar um timeout pequeno injetado no teste, ex. `timeout=0.2`, com um `sleep` de teste
  reduzido/mockado — não usar `time.sleep(1)` real dentro do teste).
- [x] T012 [P] [US2] Teste `test_error_payload_codes_connect` em `tests/test_cli_formatting.py`
  cobrindo `profile_not_found`, `already_connected`, `connect_timeout`, `sudo_denied` contra o
  schema de `ErrorPayload`.

### Implementation for User Story 2

- [x] T013 [US2] Implementar `connect_command(controller, profile: str, timeout: float) -> dict` em
  `cli/commands.py` (depende de T009/T004): valida perfil existe (`profile_not_found`), valida
  `state == disconnected` (`already_connected`), chama `controller.select_profile` +
  `controller.start_connection()`, entra no laço de `tick()` a cada 1s até `CONNECTED` ou timeout
  (`connect_timeout`) conforme `research.md` §3; captura falha de `sudo -n` reportada pelo backend
  como `sudo_denied`; qualquer outra exceção não mapeada vira `internal_error`. Sucesso retorna
  `formatting.status_payload(controller)`; falha retorna `formatting.error_payload(code, message_pt_br)`.
- [x] T014 [US2] Ligar o subcomando `connect` em `cli/dispatch.py` a `commands.connect_command`,
  com `--timeout` (default 20, `research.md` §3) e exit code `1` em qualquer `ErrorPayload`.

**Checkpoint**: `status` + `connect` funcionais e testáveis, sem quebrar US1.

---

## Phase 5: User Story 3 - Desconectar por fora (Priority: P3)

**Goal**: `openfortivpn-gui disconnect [--json]` encerra a conexão ativa, inclusive uma iniciada por outro processo (GUI ou `connect` anterior).

**Independent Test**: conectar via GUI ou `connect`, depois rodar `disconnect` num processo separado e confirmar via `status` que caiu; rodar `disconnect` sem conexão ativa e confirmar `not_connected`.

### Tests for User Story 3 ⚠️

- [x] T015 [P] [US3] Teste `test_disconnect_success`, `test_disconnect_not_connected` em
  `tests/test_cli_commands.py`, incluindo o caso "sessão reconstruída via `initialize()` sem PID
  em memória" (simula processo separado do que conectou) para confirmar que cai no fallback já
  existente sem lançar exceção.
- [x] T016 [P] [US3] Teste `test_error_payload_not_connected` em `tests/test_cli_formatting.py`.

### Implementation for User Story 3

- [x] T017 [US3] Implementar `disconnect_command(controller) -> dict` em `cli/commands.py`: chama
  `controller.initialize()` + valida `state != disconnected` (`not_connected`), senão
  `controller.stop_connection()`; captura falha de `sudo -n` como `sudo_denied`. Sucesso retorna
  `formatting.status_payload(controller)`; falha retorna `formatting.error_payload(...)`.
- [x] T018 [US3] Ligar o subcomando `disconnect` em `cli/dispatch.py` a `commands.disconnect_command`,
  exit code `1` em `ErrorPayload`.

**Checkpoint**: os 3 comandos funcionais — feature completa.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: cobertura do próprio dispatch, validação end-to-end e atualização de documentação
(exigida pela constitution — README como fonte de verdade externa).

- [x] T019 [P] Teste `test_dispatch_routes_to_cli`, `test_dispatch_falls_back_to_gui`,
  `test_dispatch_invalid_args_exit_code_2` em `tests/test_cli_dispatch.py` — só parsing de `argv`
  e decisão CLI vs GUI, sem tocar no controller real.
- [x] T020 Rodar a suíte completa `python3 -m pytest tests/` e confirmar 0 falhas antes de seguir.
- [ ] T021 Validar manualmente o roteiro de `quickstart.md` (os 5 passos) num ambiente com
  `sudo -n openfortivpn` configurado.
- [x] T022 [P] Atualizar `AGENTS.md` documentando o novo modo CLI (issue #8): seção "Estrutura"
  (novo pacote `cli/`) e "Arquitetura / fluxo" (dispatch no entrypoint, contrato de
  `status --json`, comportamento de `connect`/`disconnect`).
- [x] T023 [P] Atualizar `README.md` com instruções de uso da CLI (`status`/`connect`/`disconnect`),
  conforme a regra de governança "README como fonte de verdade externa" da constitution.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências.
- **Foundational (Phase 2)**: depende do Setup — BLOQUEIA todas as user stories.
- **User Stories (Phase 3-5)**: todas dependem do Foundational; entre si, US1 → US2 → US3 é a
  ordem de prioridade recomendada (US2 e US3 reaproveitam `status_payload`/`error_payload` de
  T004/T009, então na prática ficam mais simples depois de US1 estar pronta, mesmo sem dependência
  dura de dados entre elas).
- **Polish (Phase 6)**: depende de todas as user stories desejadas estarem completas.

### Parallel Opportunities

- T004 e T005 (Phase 2) são independentes entre si e de T002/T003 — podem rodar em paralelo.
- Dentro de cada user story, as tarefas de teste marcadas `[P]` (ex. T007+T008, T011+T012,
  T015+T016) podem rodar em paralelo entre si, mas não em paralelo com a implementação da mesma
  story (dependem do teste existir primeiro).
- T022 e T023 (documentação) são independentes entre si e podem rodar em paralelo com T021.

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 (Setup) → Phase 2 (Foundational) → Phase 3 (US1).
2. Parar e validar `status --json` isoladamente (T007-T010).
3. Esse é o MVP mínimo que já resolve o caso de uso original da issue #8 (Farol consultando status).

### Incremental Delivery

1. Setup + Foundational → base pronta.
2. US1 (status) → testável e entregável sozinho.
3. US2 (connect) → testável e entregável sozinho, sem quebrar US1.
4. US3 (disconnect) → testável e entregável sozinho, sem quebrar US1/US2.
5. Polish (Phase 6) → gate completo + documentação.
