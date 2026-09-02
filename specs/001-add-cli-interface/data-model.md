# Phase 1 Data Model: Interface CLI Programática

Todas as entidades abaixo já existem internamente (`core/models/`) — esta feature não cria domínio
novo, apenas define os DTOs de saída (`StatusPayload`/`ErrorPayload`) que expõem esse domínio já
existente através de `status --json`. Ver `contracts/status-schema.json` para o schema formal.

## Entidades existentes reaproveitadas (sem alteração)

- **`ConnectionState`** (`core/models/connection_state.py`) — `str, Enum`: `"disconnected"` |
  `"connecting"` | `"connected"`. Já serializa como string; usado diretamente como campo `state`.
- **`ConnectionSession`** (`core/models/connection_session.py`) — campos `profile`, `pid`, `iface`,
  `started_at`; método `elapsed_seconds()` já calcula o tempo decorrido. `pid` **não** é exposto no
  DTO externo (ver decisão abaixo) — é detalhe interno de implementação, sem valor para um
  consumidor programático e sem necessidade declarada em nenhum requisito da spec.
- **Perfil VPN** — hoje representado apenas como `str` (nome) na lista `controller.profiles`; sem
  mudança.

## Novo: `StatusPayload` (saída de `status --json`, e saída de sucesso de `connect`/`disconnect`)

| Campo | Tipo | Origem | Observações |
|---|---|---|---|
| `state` | `string` (enum) | `controller.state.value` | `"disconnected"` \| `"connecting"` \| `"connected"` |
| `selected_profile` | `string \| null` | `controller.selected_profile` | Nome do perfil atualmente selecionado, mesmo se não conectado |
| `profiles` | `string[]` | `controller.profiles` | Lista de nomes de perfis disponíveis (administrados + do usuário) |
| `session` | `SessionPayload \| null` | `controller.session` | `null` quando `state != "connected"` |

### `SessionPayload` (sub-objeto de `session`, presente só quando conectado)

| Campo | Tipo | Origem | Observações |
|---|---|---|---|
| `profile` | `string` | `session.profile` | Perfil da conexão ativa |
| `iface` | `string \| null` | `session.iface` | Interface `tun*`/`ppp*` detectada |
| `started_at` | `number \| null` | `session.started_at` | Epoch seconds (UTC) |
| `elapsed_seconds` | `number \| null` | `session.elapsed_seconds()` | Calculado no momento da chamada |

## Novo: `ErrorPayload` (saída de falha de qualquer subcomando, exit code 1)

| Campo | Tipo | Observações |
|---|---|---|
| `error.code` | `string` (enum, snake_case, inglês) | Ver valores abaixo — é o campo que um consumidor programático usa para decidir o que aconteceu (Clarifications, spec.md) |
| `error.message` | `string` | Mensagem legível **em português** — só para exibição humana, nunca a única forma de identificar o erro (Clarifications, spec.md) |

### Valores de `error.code`

| Código | Quando ocorre | Comando(s) |
|---|---|---|
| `profile_not_found` | `connect <perfil>` com nome que não existe em `controller.profiles` | `connect` |
| `already_connected` | `connect` chamado com `state != "disconnected"` | `connect` |
| `not_connected` | `disconnect` chamado com `state == "disconnected"` | `disconnect` |
| `connect_timeout` | `connect` não confirmou `CONNECTED` dentro do timeout (ver `research.md` §3) | `connect` |
| `sudo_denied` | `sudo -n` falhou (regra de sudo não permite sem senha) | `connect`, `disconnect` |
| `internal_error` | Qualquer falha não mapeada nos códigos acima (ex.: exceção inesperada) | qualquer |

## Contrato de saída por comando

- **`status [--json]`**: sempre imprime `StatusPayload` (texto humano formatado em PT-BR sem
  `--json`; JSON estruturado com `--json`). Nunca falha com `ErrorPayload` em uso normal — é
  somente leitura.
- **`connect <perfil>`**: sucesso → imprime `StatusPayload` atualizado (já refletindo `"connected"`)
  e sai com `0`; falha → imprime `ErrorPayload` e sai com `1`.
- **`disconnect`**: sucesso → imprime `StatusPayload` atualizado (já refletindo `"disconnected"`) e
  sai com `0`; falha → imprime `ErrorPayload` e sai com `1`.
- Todos os três comandos aceitam `--json` para forçar saída estruturada; sem a flag, a saída é
  texto legível em português (formato exato a critério da implementação, sem contrato formal —
  apenas `--json` é um contrato estável, conforme FR-009).
