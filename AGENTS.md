# AGENTS.md — openfortivpn-gui

## O que é

Script único em Python (`openfortivpn-gui`), GTK3 + AppIndicator3, que dá uma interface
gráfica (janela + ícone de bandeja) para ligar/desligar túneis `openfortivpn` e acompanhar
tempo de conexão e histórico. Não há build step nem dependências empacotadas — é executado
diretamente via shebang `#!/usr/bin/env python3`.

## Estrutura

- `openfortivpn-gui` — todo o código-fonte (classe `VpnApp(Gtk.Application)`), único arquivo.
- `README.md` — instalação e uso.
- Instalado via symlink em `~/.local/bin/openfortivpn-gui` (fora deste repo, não versionado).

## Arquitetura / fluxo

- Estado é uma máquina de 3 estados: `disconnected` / `connecting` / `connected`, guiada por
  `GLib.timeout_add_seconds(1, self._tick)` que roda a cada segundo.
- Detecção de "conectado" é uma heurística dupla:
  - `_running()`: `pgrep -x openfortivpn` (processo existe).
  - `tunnel_iface()`: existe alguma interface `ppp*`/`tun*` em `/sys/class/net`.
  - **Limitação conhecida**: `tunnel_iface()` não valida que a interface pertence à sessão
    atual — qualquer túnel `tun*`/`ppp*` de outra origem (outra VPN concorrente) causa falso
    positivo. Ver issue de robustez sobre isso.
- Conectar/desconectar chama `sudo -n openfortivpn -c <perfil>` / `sudo -n pkill -x openfortivpn`.
  Depende de regra de sudo NOPASSWD (não gerenciada por este projeto) para as duas operações.
- Perfis de VPN vêm de `/etc/openfortivpn/` (arquivo `config` ou `*.conf`), listados uma única
  vez no `__init__` — não há refresh automático se o admin adicionar/remover perfis com o app
  já aberto.
- Persistência de estado do app (não da VPN em si):
  - `~/.config/openfortivpn-gui/state.json` — último perfil usado.
  - `~/.config/openfortivpn-gui/history.json` — histórico de sessões, com purga automática de
    registros com mais de 7 dias (`RETENTION_SECONDS`).
  - `/tmp/openfortivpn-gui.log` — stdout/stderr do processo `openfortivpn` lançado via `sudo`.
  - `/tmp/openfortivpn-gui.start` — timestamp epoch do início da sessão ativa, usado para
    recalcular o tempo decorrido se a GUI for reaberta com a VPN já conectada.

## Decisões relevantes

- Uso de `sudo -n` (não interativo): a app nunca deve pedir senha via terminal; se a regra de
  sudo não permitir a operação sem senha, o `Popen` falha silenciosamente e o app só percebe
  pela ausência do processo no `_tick` seguinte (mensagem genérica "Falha ao conectar").
- `Gtk.Application` com `application_id="local.openfortivpn.gui"` fixo garante singleton via
  D-Bus — abrir o app duas vezes reativa a janela existente em vez de duplicar processo.
- `stopping_until` (grace period de 3s após `stop()`) existe para o `_tick` não interpretar a
  própria desconexão solicitada pelo usuário como "caiu sozinho".

## Limitações conhecidas (candidatas a issues de robustez)

1. `tunnel_iface()` não distingue a interface criada por esta sessão de outra pré-existente.
2. `pkill -x openfortivpn` mata por nome de processo, não por PID guardado do `Popen`.
3. `LOG`/`START_FILE` usam caminhos fixos e previsíveis em `/tmp` (compartilhado entre
   usuários), sem proteção contra symlink attack.
4. `Popen` do `openfortivpn` não trata stdin — perfil que exija autenticação interativa
   (token/OTP) travaria esperando input que nunca chega.
5. Nenhuma checagem de exit code do processo lançado via `sudo`; diagnóstico de falha só existe
   no `/tmp/openfortivpn-gui.log`, sem qualquer indicação na UI.
6. `self.profiles` é calculado uma vez no `__init__` e nunca recarregado.

## Convenções

- Sem framework de build/testes ainda — mudanças são validadas rodando o script manualmente.
- Mensagens de UI e notificações são em português (usuário final é PT-BR).
- Commits e PRs neste repo não levam rodapé de atribuição de IA.
