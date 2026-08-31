# AGENTS.md — openfortivpn-gui

## O que é

GUI pessoal em Python, GTK3 + AppIndicator3, que dá uma interface gráfica (janela + ícone de
bandeja) para ligar/desligar túneis `openfortivpn` e acompanhar tempo de conexão e histórico.
Não há build step — é executado diretamente via shebang `#!/usr/bin/env python3`. O código
começou como script único (tag `pre-refactor`) e foi extraído para uma arquitetura em camadas
(contratos → services → controller → ui); o comportamento observável não mudou, mas a estrutura
interna sim.

## Estrutura

- `openfortivpn-gui` — shim fino de entrypoint: só faz `sys.path.insert` do diretório do
  próprio arquivo, `from ui.application import VpnApp` e `app.run(None)`. Não tem lógica própria.
- `core/interfaces/` — contratos ABC que desacoplam o controller de implementação concreta:
  `VpnBackend` (iniciar/parar o processo openfortivpn), `TunnelStateDetector` (detectar
  interface de túnel ativa), `ProfileSource` (listar perfis disponíveis), `AppStateStore` e
  `HistoryStore` (persistência de estado da app e de histórico de sessões).
- `core/models/` — dataclasses de domínio, sem dependência de GTK: `ConnectionState` (Enum:
  `DISCONNECTED`/`CONNECTING`/`CONNECTED`), `ConnectionSession`, `HistoryRecord`,
  `ConnectOutcome`, `ControllerEvent`.
- `services/` — implementações concretas dos contratos: `OpenfortivpnBackend`,
  `SysfsTunnelDetector`, `FilesystemProfileSource`, `JsonAppStateStore` + `JsonHistoryStore`,
  `CommandRunner` (Protocol para execução de comandos, permite dublê em teste),
  `runtime_paths.resolve_runtime_dir()` (resolve o diretório de runtime da app).
- `controller/vpn_controller.py` — `VpnController`: máquina de estados pura (sem GTK), orquestra
  os 5 contratos acima e expõe `tick()` para a UI consumir.
- `ui/` — camada GTK/AppIndicator: `application.py` (`VpnApp(Gtk.Application)`, monta e injeta as
  implementações concretas de `services/` no `VpnController`), `connect_page.py`,
  `history_page.py`, `tray_indicator.py`, `formatting.py`.
- `tests/` — suíte pytest (64 testes) cobrindo `core/models`, `services` e `controller` com
  fakes/dublês (via `CommandRunner` e os contratos ABC). A camada `ui/` (GTK/AppIndicator) não é
  testada automaticamente — validação é por smoke test manual.
- `requirements.txt` (dependências de runtime) / `requirements/dev.txt` (+ pytest) / `pytest.ini`.
- `README.md` — instalação e uso.
- Instalado via symlink em `~/.local/bin/openfortivpn-gui` (fora deste repo, não versionado).

## Arquitetura / fluxo

- Estado é uma máquina de 3 estados (`ConnectionState.DISCONNECTED` / `CONNECTING` /
  `CONNECTED`) que vive inteiramente em `VpnController`, sem nenhuma dependência de GTK. A UI
  (`ui/application.py`) apenas chama `GLib.timeout_add_seconds(1, ...)` para invocar
  `controller.tick()` a cada segundo e traduz a lista de `ControllerEvent` retornada em
  notificações e atualizações visuais (label, ícone de bandeja, aba de histórico).
- Detecção de interface conectada usa snapshot de baseline: antes de conectar, o
  `TunnelStateDetector` registra quais interfaces `tun*`/`ppp*` já existiam, e só considera
  "conectado" uma interface nova em relação a esse baseline — evita falso positivo por túnel de
  outra origem já presente no sistema (issue #1, corrigida).
- Reattach (app reaberto com a VPN já conectada por fora) usa a interface salva em
  `AppStateStore` quando disponível; sem interface salva, cai na heurística de último recurso
  "qualquer `tun*`/`ppp*` presente" (ver Limitações conhecidas).
- Conectar chama `sudo -n openfortivpn -c <perfil>` via `OpenfortivpnBackend`, com stdin fechado
  explicitamente (perfil que exigisse input interativo travaria o processo sem isso — issue #4,
  corrigida).
- `stop()` sinaliza o PID rastreado do processo lançado (`sudo -n kill -TERM <pid>`); o fallback
  para `pkill -x openfortivpn` só é usado quando o PID é desconhecido (caso de reattach sem PID
  salvo). Não há escalonamento para SIGKILL nem espera bloqueante pela morte do processo —
  decisão deliberada para não travar a UI single-thread do GTK.
- Diagnóstico de falha ao conectar inclui exit code e motivo, reportados na UI (issue #5,
  corrigida) — antes só existiam no log.
- Perfis de VPN vêm de `/etc/openfortivpn/` (arquivo `config` ou `*.conf`) e são recarregados a
  cada `tick()` via `ProfileSource` — perfil adicionado/removido pelo admin aparece sem reiniciar
  o app (issue #6, corrigida).
- Persistência de estado do app (não da VPN em si), via `services/runtime_paths.py`:
  - `~/.config/openfortivpn-gui/state.json` — último perfil usado e interface de reattach
    (`JsonAppStateStore`).
  - `~/.config/openfortivpn-gui/history.json` — histórico de sessões, com purga automática de
    registros com mais de 7 dias (`JsonHistoryStore`).
  - `$XDG_RUNTIME_DIR/openfortivpn-gui/` (fallback `~/.cache/openfortivpn-gui/` se
    `XDG_RUNTIME_DIR` não estiver definido) — log (stdout/stderr do processo `openfortivpn`
    lançado via `sudo`) e marcador de sessão ativa (timestamp de início, para recalcular o tempo
    decorrido se a GUI for reaberta com a VPN já conectada). Movido de `/tmp` (issue #3,
    corrigida) para um diretório privado por usuário, sem risco de symlink attack.

## Decisões relevantes

- Uso de `sudo -n` (não interativo): a app nunca deve pedir senha via terminal; se a regra de
  sudo não permitir a operação sem senha, o `Popen` falha silenciosamente e o app só percebe
  pela ausência do processo no `_tick` seguinte (mensagem genérica "Falha ao conectar").
- `Gtk.Application` com `application_id="local.openfortivpn.gui"` fixo garante singleton via
  D-Bus — abrir o app duas vezes reativa a janela existente em vez de duplicar processo.
- `stopping_until` (grace period de 3s após `stop()`) existe para o `_tick` não interpretar a
  própria desconexão solicitada pelo usuário como "caiu sozinho".

## Limitações conhecidas

As 6 limitações originais (issues #1–#6) foram corrigidas na refatoração modular — ver
"Arquitetura / fluxo" acima para o que mudou em cada caso. Limitações residuais aceitas
deliberadamente:

1. `stop()` não escalona para SIGKILL nem espera confirmação de que o processo morreu — decisão
   consciente para não bloquear a thread única do GTK.
2. Reattach sem sessão salva com interface conhecida ainda usa como último recurso a heurística
   "qualquer `tun*`/`ppp*` presente", com o mesmo risco de falso positivo por túnel concorrente
   que o baseline resolve no caso normal.

Próximo trabalho planejado: issue #7 (permitir configurar novos perfis de VPN pela interface,
com ícone por perfil).

## Convenções

- Suíte de testes roda com `python3 -m pytest tests/` (instalar `requirements/dev.txt` antes).
- Mensagens de UI e notificações são em português (usuário final é PT-BR).
- Commits e PRs neste repo não levam rodapé de atribuição de IA.
