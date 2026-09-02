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
  interface de túnel ativa), `ProfileSource` (listar perfis disponíveis, resolver o caminho
  completo de um perfil pelo nome — `resolve_path()` — e indicar se é editável pela GUI —
  `is_user_profile()`), `ProfileWriter` (persistir o conteúdo de um perfil criado/editado pela
  GUI), `ProfileIconStore` (associar ícone a perfil), `AppStateStore` e `HistoryStore`
  (persistência de estado da app e de histórico de sessões).
- `core/models/` — dataclasses de domínio, sem dependência de GTK: `ConnectionState` (Enum:
  `DISCONNECTED`/`CONNECTING`/`CONNECTED`), `ConnectionSession`, `HistoryRecord`,
  `ConnectOutcome`, `ControllerEvent`.
- `services/` — implementações concretas dos contratos: `OpenfortivpnBackend`,
  `SysfsTunnelDetector`, `FilesystemProfileSource` (mescla perfis administrados em
  `/etc/openfortivpn` com perfis criados pela GUI em `~/.config/openfortivpn-gui/profiles/`;
  em colisão de nome, o perfil administrado tem prioridade), `FilesystemProfileWriter` (só
  escreve no diretório de perfis do usuário — nunca em `/etc/openfortivpn`, que permanece
  somente-leitura pela GUI), `JsonProfileIconStore` (mapa perfil → ícone, em
  `~/.config/openfortivpn-gui/profile_icons.json`), `profile_config.py` (funções puras:
  `validate_new_profile()`, `sanitize_profile_filename()`, `build_profile_config()`,
  `parse_profile_config()` (lê um `.conf` existente de volta para campos, usado ao abrir o
  diálogo em modo edição e para preservar campos desconhecidos como `trusted-cert` num
  round-trip) — regra de negócio de criação/edição de perfil, sem GTK, totalmente testável),
  `JsonAppStateStore` + `JsonHistoryStore`, `CommandRunner` (Protocol para execução de comandos,
  permite dublê em teste), `runtime_paths.py` (`resolve_runtime_dir()` e
  `resolve_user_profile_dir()`).
- `controller/vpn_controller.py` — `VpnController`: máquina de estados pura (sem GTK), orquestra
  os contratos acima e expõe `tick()` para a UI consumir. `refresh_profiles()` expõe a mesma
  releitura de perfis que `tick()` faz periodicamente, mas sob demanda — usada pela UI logo após
  criar um perfil pela GUI, para não esperar o próximo tick (issue #7).
- `ui/` — camada GTK/AppIndicator: `application.py` (`VpnApp(Gtk.Application)`, monta e injeta as
  implementações concretas de `services/` no `VpnController`), `connect_page.py`,
  `history_page.py`, `tray_indicator.py`, `formatting.py`, `icons.py` (resolve nome de ícone do
  tema ou caminho de arquivo para `GdkPixbuf.Pixbuf`, com fallback para ícone padrão
  `network-vpn`), `profile_dialog.py` (`Gtk.Dialog` de criação/edição de perfil: nome, host,
  porta, usuário, senha e ícone opcional via `Gtk.FileChooserButton`; em modo edição o campo
  nome fica travado e os demais vêm pré-preenchidos a partir do `.conf` existente).
- `cli/` — interface de linha de comando programática (issue #8, corrigida): `dispatch.py`
  (`is_cli_invocation()` decide se `argv` começa por um dos subcomandos reconhecidos —
  `status`/`connect`/`disconnect` — usado pelo entrypoint antes de importar GTK; `main()` faz o
  parse com `argparse` e resolve o exit code), `wiring.py` (`build_controller()` monta o mesmo
  `VpnController` com as mesmas implementações de `services/` usadas pela GUI — fonte única de
  verdade sobre como montar o controller), `commands.py` (`status_command()`, `connect_command()`
  — bloqueia fazendo *polling* de `controller.tick()` a cada 1s até confirmar ou até o timeout —,
  `disconnect_command()`), `formatting.py` (serializa `StatusPayload`/`ErrorPayload` e formata
  texto legível em PT-BR para o modo sem `--json`). Nenhum módulo de `cli/` importa `gi`/`Gtk`.
- `tests/` — suíte pytest (130 testes) cobrindo `core/models`, `services`, `controller` e `cli/`
  com fakes/dublês (via `CommandRunner` e os contratos ABC). A camada `ui/` (GTK/AppIndicator) não
  é testada automaticamente — validação é por smoke test manual (`dev/render_smoke.sh`).
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
- Perfis de VPN vêm da mescla de `/etc/openfortivpn/` (administrado, somente-leitura pela GUI) e
  `~/.config/openfortivpn-gui/profiles/` (criados pela própria GUI) — arquivos `config` ou
  `*.conf` em qualquer um dos dois, recarregados a cada `tick()` via `ProfileSource` — perfil
  adicionado/removido por qualquer via aparece sem reiniciar o app (issue #6, corrigida).
- Criar perfil pela GUI (issue #7, corrigida) é feito só em `~/.config/openfortivpn-gui/profiles/`
  — deliberadamente nunca em `/etc/openfortivpn/`, para não exigir escrita privilegiada
  (`sudo tee` ou equivalente) nem risco de senha interativa. `openfortivpn -c <caminho>` aceita
  qualquer caminho, e o processo já roda via `sudo -n`, que consegue ler o arquivo do usuário
  normalmente — não há necessidade de mover o perfil para `/etc`. Ao salvar, a UI chama
  `VpnController.refresh_profiles()` para o novo perfil aparecer imediatamente no combo da janela
  e no submenu da bandeja, sem esperar o próximo `tick()`.
- Editar perfil (botão "✎" na janela / "Editar perfil selecionado…" na bandeja) só é permitido
  para perfis em `~/.config/openfortivpn-gui/profiles/` (`ProfileSource.is_user_profile()`);
  tentar editar um perfil administrado em `/etc/openfortivpn/` mostra uma notificação e não abre
  o diálogo. O nome do perfil não pode ser alterado na edição (evitaria ter que mover arquivo,
  atualizar último perfil selecionado, histórico etc. — fora do escopo). Campos do `.conf` que a
  UI não edita diretamente (ex.: `trusted-cert`) são preservados via
  `profile_config.parse_profile_config()`/`build_profile_config(..., extra=...)`.
- Ícone por perfil (issue #7) é resolvido por `ui/icons.load_profile_pixbuf()`: se o valor salvo
  em `ProfileIconStore` começa com `/`, é tratado como caminho de arquivo de imagem; caso
  contrário, como nome de ícone do tema GTK ativo. Sem valor configurado, ou em caso de falha ao
  carregar, cai no ícone padrão `network-vpn`.
- Interface CLI programática (issue #8, corrigida): o entrypoint `openfortivpn-gui` (raiz) decide
  entre modo GUI e modo CLI *antes* de `from ui.application import VpnApp` (e portanto antes de
  puxar GTK), via `cli.dispatch.is_cli_invocation(sys.argv[1:])` — `argv` começando por `status`,
  `connect` ou `disconnect` cai no modo CLI; qualquer outro caso (sem argumentos, ou argumento não
  reconhecido) abre a GUI, comportamento idêntico ao anterior a esta feature. O modo CLI reaproveita
  o mesmo `VpnController` e os mesmos `services/` já usados pela GUI, montados por
  `cli/wiring.build_controller()` — não há duplicação de regra de negócio entre os dois modos.
  `status --json` tem contrato de saída estável e documentado em
  `specs/001-add-cli-interface/contracts/` (schema JSON e tabela de exit codes); a saída sem
  `--json` é texto formatado, sem contrato formal. Segue a mesma decisão de idioma do resto do
  projeto: código (nomes de módulos, campos do payload, `error.code`) estruturado em inglês,
  mensagens voltadas ao usuário (`error.message`, texto humano) em PT-BR.
- Persistência de estado do app (não da VPN em si), via `services/runtime_paths.py`:
  - `~/.config/openfortivpn-gui/state.json` — último perfil usado e interface de reattach
    (`JsonAppStateStore`).
  - `~/.config/openfortivpn-gui/history.json` — histórico de sessões, com purga automática de
    registros com mais de 7 dias (`JsonHistoryStore`).
  - `~/.config/openfortivpn-gui/profiles/` — perfis de VPN criados pela GUI (`.conf`, modo
    `0600`, diretório `0700` — contêm senha em texto plano, mesmo formato usado pelo próprio
    openfortivpn em `/etc/openfortivpn/`).
  - `~/.config/openfortivpn-gui/profile_icons.json` — mapa nome do perfil → ícone
    (`JsonProfileIconStore`).
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

As 8 issues originais (#1–#8) foram corrigidas/implementadas — ver "Arquitetura / fluxo" acima
para o que mudou em cada caso. Limitações residuais aceitas deliberadamente:

1. `stop()` não escalona para SIGKILL nem espera confirmação de que o processo morreu — decisão
   consciente para não bloquear a thread única do GTK.
2. Reattach sem sessão salva com interface conhecida ainda usa como último recurso a heurística
   "qualquer `tun*`/`ppp*` presente", com o mesmo risco de falso positivo por túnel concorrente
   que o baseline resolve no caso normal.
3. O submenu de perfis da bandeja usa `Gtk.ImageMenuItem` (obsoleto no GTK3, mas funcional) para
   mostrar ícone por item — não há indicador de rádio nativo, o perfil selecionado é marcado por
   prefixo "●" no rótulo; o submenu só é reconstruído quando a seleção muda de fato (não a cada
   tick), para não recriar o menu inteiro a cada segundo.
4. O diálogo de criação/edição de perfil (`ui/profile_dialog.py`) cobre os campos essenciais do
   openfortivpn (host, porta, usuário, senha) — campos avançados do formato de config (ex.:
   `trusted-cert`, `otp`) não têm UI dedicada; ao editar um perfil que já os tenha, eles são
   preservados no arquivo, mas quem precisar criá-los do zero ainda edita o `.conf` manualmente.
5. Perfis administrados em `/etc/openfortivpn/` não podem ser editados nem renomeados pela GUI —
   só perfis criados por ela mesma, em `~/.config/openfortivpn-gui/profiles/`.
6. `disconnect` via CLI, quando chamado por um processo diferente do que iniciou a conexão (ex.:
   conectou pela GUI, desconectou pela CLI, ou vice-versa), não conhece o PID exato da sessão e
   cai no mesmo fallback "matar por nome" (`pkill -x openfortivpn`) já usado pelo reattach sem PID
   salvo — ver `stop()` em "Arquitetura / fluxo". Decisão de escopo deliberada da issue #8
   (`research.md`/`data-model.md` da feature), não um bug: o PID interno de `ConnectionSession`
   nunca é exposto fora do processo que o guarda, então um processo externo não teria como
   endereçar o processo exato mesmo se quisesse.

## Convenções

- Suíte de testes roda com `python3 -m pytest tests/` (instalar `requirements/dev.txt` antes).
- Mensagens de UI e notificações são em português (usuário final é PT-BR).
- Commits e PRs neste repo não levam rodapé de atribuição de IA.

## Renderização headless para inspeção visual

`dev/render_smoke.sh [saida.png] [--page connect|history]` sobe um Xvfb (ou reusa um `DISPLAY`
já existente via `xvfb-run`, se disponível), ativa a `VpnApp` real com
`application_id="local.openfortivpn.gui.dev"` (não colide com uma instância de produção) e
salva um screenshot PNG da janela principal. Não conecta nenhuma VPN de verdade — só renderiza
a UI. Útil para verificar mudanças de CSS/layout sem precisar de display físico.
