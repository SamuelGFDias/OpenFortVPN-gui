# Phase 0 Research: Interface CLI Programática

Não há itens `NEEDS CLARIFICATION` pendentes no Technical Context — as decisões abaixo consolidam
escolhas técnicas concretas a partir da investigação já feita sobre o código atual (wiring do
`VpnController`, `services/openfortivpn_backend.py`, `services/json_state_store.py`) e das
clarificações já resolvidas na spec.

## 1. Dispatch CLI vs GUI no entrypoint

**Decision**: `openfortivpn-gui` (raiz) ganha um `argparse.ArgumentParser` com subparsers
(`status`, `connect`, `disconnect`) verificado **antes** de `from ui.application import VpnApp`.
Se `sys.argv[1:]` corresponder a um subcomando reconhecido, despacha para `cli.dispatch.main()` e
sai sem importar `ui.application`. Caso contrário (nenhum argumento, ou argumento não reconhecido
por um subcomando), cai no comportamento atual (`VpnApp().run(None)`), preservando 100% de
compatibilidade com o uso hoje (ex.: ícone `.desktop` que chama o binário sem argumentos).

**Rationale**: `import gi` só acontece dentro de `ui/application.py`; adiar esse import para depois
da decisão de dispatch é o que garante que o modo CLI funcione sem `DISPLAY`/Xvfb, sem exigir
mudança em `ui/`.

**Alternatives considered**:
- Sempre importar `ui.application` e decidir depois — rejeitado: forçaria import de `gi`/GTK mesmo
  em ambiente sem display (ex.: um cron job ou servidor sem X11 rodando `status --json`), quebrando
  o caso de uso principal da issue #8.
- Um binário CLI separado (`openfortivpn-gui-cli`) — rejeitado: duplica o mecanismo de
  instalação/symlink documentado no `AGENTS.md` sem benefício real; um único entrypoint com
  dispatch é mais simples de instalar e descobrir.

## 2. Wiring headless do VpnController

**Decision**: `cli/wiring.py` expõe uma função `build_controller() -> VpnController` que
instancia `OpenfortivpnBackend()`, `SysfsTunnelDetector()`, `FilesystemProfileSource()`,
`JsonAppStateStore()`, `JsonHistoryStore()` e monta o `VpnController` — literalmente o mesmo
código de `ui/application.py:38-48`, extraído para ser reaproveitado tanto pela GUI quanto pela
CLI (a GUI passa a chamar essa função também, eliminando a duplicação em vez de criar uma segunda
cópia do wiring).

**Rationale**: evita duas fontes de verdade para "como montar o controller" — se um novo service
concreto for injetado no futuro (ex.: uma nova implementação de `TunnelStateDetector`), só precisa
mudar em um lugar.

**Alternatives considered**: duplicar o wiring dentro de `cli/` — rejeitado: viola o próprio
Princípio I da constitution na prática (duas implementações do mesmo wiring divergem com o tempo).

## 3. `connect` bloqueante com timeout

**Decision**: após `controller.select_profile(nome)` e `controller.start_connection()`, `cli/commands.py`
entra num laço síncrono chamando `controller.tick()` a cada 1 segundo (mesmo intervalo que
`GLib.timeout_add_seconds(1, ...)` já usa na GUI, `ui/application.py:135`) até que `controller.state`
mude para `CONNECTED` ou até que um evento `connect_failed`/`cancelled` seja emitido, com um timeout
padrão de **20 segundos** (múltiplo folgado do tempo típico de handshake TLS/PPP observado por
`openfortivpn`, evitando falso-negativo em rede mais lenta). Esgotado o timeout sem confirmação, o
comando retorna falha com mensagem indicando que o processo pode ainda estar subindo e sugerindo
`status` para confirmar depois — sem matar o processo.

**Rationale**: reaproveita o mesmo mecanismo de tick que a GUI já usa (sem inventar um novo
caminho de detecção de conexão), só trocando o agendamento assíncrono do GLib por um laço síncrono
de processo de vida curta — consistente com a decisão já tomada na spec (FR-003, Assumptions).

**Alternatives considered**: aguardar um evento explícito (ex.: watch em `active_session.json` via
inotify) — rejeitado: mais complexo, e o `tick()` já centraliza toda a lógica de detecção
(baseline de interface, diagnóstico de falha) — reimplementar isso por fora duplicaria regra de
negócio, violando o Princípio I.

## 4. Exit codes

**Decision**: convenção simples e documentada em `contracts/cli-commands.md`:
- `0` — sucesso.
- `1` — falha reportada pelo domínio (perfil inexistente, já conectado, nada para desconectar,
  timeout de `connect`, falha de `sudo -n`).
- `2` — uso inválido da CLI (argumento faltando/malformado) — delegado ao comportamento padrão do
  próprio `argparse`, que já usa exit code `2` para esse caso.

**Rationale**: a spec (SC-004) só exige que falhas sejam "identificáveis programaticamente pelo
código de saída", sem exigir granularidade por tipo de erro — um script chamador (ex.: Farol)
precisa apenas distinguir sucesso de falha; o campo `error` estruturado do JSON (ver `data-model.md`)
é quem carrega o motivo específico, não o exit code.

**Alternatives considered**: um exit code distinto por tipo de erro (ex.: `3` = perfil inexistente,
`4` = já conectado) — rejeitado por ora: aumenta a superfície de contrato sem necessidade
comprovada; pode ser adicionado depois de forma aditiva (MINOR na constitution) se um consumidor
real precisar.

## 5. Schema de `status --json`

**Decision**: ver `data-model.md` e `contracts/status-schema.json` para o schema completo. Campos
estruturados (`state`, `selected_profile`, `profiles`, `session.*`, `error.code`) em
inglês/snake_case; `error.message` (quando presente) em PT-BR — conforme a clarificação já
registrada em `spec.md`.

## 6. `disconnect` cross-processo

**Decision**: nenhuma mudança em `VpnController.initialize()` ou `OpenfortivpnBackend` — `disconnect`
via CLI chama `controller.initialize()` seguido de `controller.stop_connection()`, que já cai no
fallback `pkill -x openfortivpn` quando o PID não está disponível na sessão reconstruída (comportamento
atual, documentado em `AGENTS.md`). Decisão de escopo já fechada na clarificação da spec (FR-010).

**Rationale**: manter o fallback existente evita mexer em `controller/vpn_controller.py`, reduzindo
o raio de mudança desta feature a código novo (`cli/`) mais o dispatch do entrypoint.

## 7. Estratégia de teste

**Decision**: `tests/test_cli_commands.py` reaproveita o padrão de fakes já usado em
`tests/test_vpn_controller.py` (`FakeVpnBackend`, `FakeTunnelStateDetector`, `FakeProfileSource`,
`FakeAppStateStore`, `FakeHistoryStore`), injetando um `VpnController` construído com fakes em vez
de `cli.wiring.build_controller()`. `tests/test_cli_dispatch.py` testa só o parsing de `argv` (sem
tocar no controller). Nenhum teste desta feature depende de `gi`/`Gtk` nem do binário real
`openfortivpn`.

**Rationale**: consistente com o Princípio V da constitution — testar contra os contratos ABC, não
contra GTK ou processo externo real.
