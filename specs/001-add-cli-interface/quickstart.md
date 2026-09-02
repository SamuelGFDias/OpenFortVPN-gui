# Quickstart: validar a interface CLI programática

Pré-requisito: a feature implementada (`cli/` + dispatch em `openfortivpn-gui`), ambiente com
`sudo -n openfortivpn` já configurado (mesma configuração que a GUI já exige — ver `AGENTS.md`).

## 1. Status sem nenhuma VPN conectada

```bash
./openfortivpn-gui status --json
```

Esperado: exit `0`, JSON com `"state": "disconnected"`, `"session": null`, `"profiles"` listando
os perfis já cadastrados (ver `contracts/status-schema.json`).

## 2. Conectar por CLI

```bash
./openfortivpn-gui connect <nome-do-perfil> --json
```

Esperado: bloqueia por até 20s (ou o valor de `--timeout`), depois exit `0` com
`"state": "connected"` e `"session"` preenchido — ou exit `1` com `error.code` explicando o motivo
(ex.: `profile_not_found` se o nome não existir; rode `status --json` antes para confirmar os
nomes disponíveis em `profiles`).

## 3. Confirmar por fora, com a GUI aberta ou fechada

```bash
./openfortivpn-gui status --json
```

Esperado: mesmo resultado reportado pela GUI (se estiver aberta) — `"state": "connected"`,
`session.profile` igual ao perfil conectado no passo 2.

## 4. Desconectar por CLI (inclusive uma conexão iniciada pela GUI)

```bash
./openfortivpn-gui disconnect --json
```

Esperado: exit `0`, `"state": "disconnected"`, `"session": null`. Rodar de novo sem conexão ativa
deve retornar exit `1` com `error.code: "not_connected"`.

## 5. Modo GUI continua inalterado

```bash
./openfortivpn-gui
```

Esperado: abre a janela normalmente, sem nenhuma mudança de comportamento em relação ao estado
anterior a esta feature.

## Referências

- Schema completo: [`contracts/status-schema.json`](./contracts/status-schema.json)
- Contrato de comandos e exit codes: [`contracts/cli-commands.md`](./contracts/cli-commands.md)
- Modelo de dados: [`data-model.md`](./data-model.md)
