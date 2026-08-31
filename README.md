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

## Estado e logs

- `~/.config/openfortivpn-gui/state.json` — último perfil selecionado
- `~/.config/openfortivpn-gui/history.json` — histórico de conexões
- `$XDG_RUNTIME_DIR/openfortivpn-gui/` (fallback `~/.cache/openfortivpn-gui/`) — log
  (stdout/stderr do processo `openfortivpn`) e marcador de sessão ativa

Veja `AGENTS.md` para decisões de arquitetura e limitações conhecidas.

## Desenvolvimento e testes

O código é organizado em camadas (`core/`, `services/`, `controller/`, `ui/`) — o executável
`openfortivpn-gui` é apenas um shim fino que chama `ui.application.VpnApp`. Detalhes da estrutura
estão em `AGENTS.md`.

Para rodar a suíte de testes:

```bash
python3 -m venv .venv && source .venv/bin/activate  # opcional
pip install -r requirements/dev.txt
python3 -m pytest tests/
```
