# openfortivpn-gui

GUI pessoal (GTK3 + AppIndicator3) para ligar/desligar o [openfortivpn](https://github.com/adrienverge/openfortivpn) via ícone de bandeja, com histórico de conexões e tempo decorrido.

## Requisitos

- Python 3 com `python3-gi` (PyGObject)
- GTK 3, `libappindicator3` (ou `libayatana-appindicator3`)
- `openfortivpn` instalado
- `sudo -n` configurado para o usuário conseguir rodar `openfortivpn`, `kill` e `pkill -x openfortivpn` sem senha
- Perfis de conexão em `/etc/openfortivpn/*.conf` ou `/etc/openfortivpn/config`

## Instalação

```bash
ln -s "$(pwd)/openfortivpn-gui" ~/.local/bin/openfortivpn-gui
```

Um atalho `.desktop` (`Exec=~/.local/bin/openfortivpn-gui`) pode ser criado em
`~/.local/share/applications/` para abrir pelo menu de aplicativos ou autostart.

## Uso

- Clique no botão "Ligar VPN" ou no item do menu de bandeja para conectar/desconectar.
- A aba "Histórico" lista as últimas conexões (retidas por 7 dias).
- O perfil ativo é lembrado entre execuções (`~/.config/openfortivpn-gui/state.json`).

## Uso via linha de comando

Além da GUI, `openfortivpn-gui` também funciona como CLI programática, com três subcomandos.
Chamado com um desses três nomes como primeiro argumento, abre em modo CLI (sem GTK); em
qualquer outro caso (sem argumentos, por exemplo) abre a interface gráfica normalmente.

```bash
# Consulta o estado atual (não tem efeito colateral)
openfortivpn-gui status
openfortivpn-gui status --json

# Conecta a um perfil, bloqueando até confirmar ou até o timeout (padrão: 20s)
openfortivpn-gui connect trabalho
openfortivpn-gui connect trabalho --json --timeout 30

# Desconecta a conexão ativa, de qualquer origem (GUI ou outra chamada de connect)
openfortivpn-gui disconnect
```

Todos os três aceitam `--json` para saída estruturada. Exit code `0` em sucesso, `1` em falha de
domínio (com `error.code`/`error.message` no payload) e `2` em uso inválido da CLI. A saída de
`status --json` (e a de sucesso de `connect`/`disconnect`, que é o mesmo payload) segue um
contrato estável, pensado para integração com outros programas — documentação completa do
contrato, schema JSON e códigos de erro em `specs/001-add-cli-interface/contracts/`.

## Estado e logs

- `~/.config/openfortivpn-gui/state.json` — último perfil selecionado
- `~/.config/openfortivpn-gui/history.json` — histórico de conexões
- `$XDG_RUNTIME_DIR/openfortivpn-gui/` (fallback `~/.cache/openfortivpn-gui/`) — log
  (stdout/stderr do processo `openfortivpn`) e marcador de sessão ativa

Veja `AGENTS.md` para decisões de arquitetura e limitações conhecidas.

## Desenvolvimento e testes

O código é organizado em camadas (`core/`, `services/`, `controller/`, `ui/`, `cli/`) — o
executável `openfortivpn-gui` decide entre abrir a GUI (`ui.application.VpnApp`) ou a CLI
(`cli.dispatch.main`) conforme os argumentos recebidos. Detalhes da estrutura estão em
`AGENTS.md`.

Para rodar a suíte de testes:

```bash
python3 -m venv .venv && source .venv/bin/activate  # opcional
pip install -r requirements/dev.txt
python3 -m pytest tests/
```
