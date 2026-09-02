# Feature Specification: Interface CLI Programática

**Feature Branch**: `001-add-cli-interface`

**Created**: 2026-09-02

**Status**: Draft

**Input**: User description: "Expor uma CLI programática para o openfortivpn-gui (issue #8), permitindo que processos externos (ex.: o projeto Farol) consultem o status da VPN e disparem conectar/desconectar sem precisar reimplementar a heurística interna do app nem ler arquivos internos não documentados. Decisão já tomada: CLI (não D-Bus), reaproveitando o VpnController existente."

## Clarifications

### Session 2026-09-02

- Q: Quando um comando falhar (ex.: perfil inexistente, sem conexão ativa), o campo de mensagem legível dentro da saída `--json` deve ficar em português ou em inglês? → A: Opção A — estado/código de erro estruturado sempre em inglês/snake_case (estável, para o consumidor decidir programaticamente); mensagem legível (`message`) em PT-BR, só para exibição humana, nunca para o consumidor decidir por parsing de texto.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consultar status da VPN por fora (Priority: P1)

Um processo externo (ex.: o projeto Farol, ou qualquer script de automação do usuário) precisa saber, a qualquer momento, se a VPN está conectada, a qual perfil, e há quanto tempo — sem depender da GUI estar aberta e sem ler diretamente os arquivos internos de estado do app (que hoje não são um contrato público e podem mudar de formato a qualquer release).

**Why this priority**: É o caso de uso mais imediato (motivação original da issue #8, plugin do Farol) e o de menor risco — é somente leitura, não altera o estado da VPN. Sem ele, nenhum outro consumidor externo consegue nem verificar se vale a pena disparar `connect`/`disconnect`.

**Independent Test**: Pode ser testado sozinho rodando `openfortivpn-gui status --json` em qualquer combinação de estado (desconectado / conectando / conectado) e validando que a saída reflete o estado real do processo `openfortivpn` no sistema, com ou sem a GUI aberta.

**Acceptance Scenarios**:

1. **Given** nenhuma VPN conectada e a GUI fechada, **When** um processo externo roda `openfortivpn-gui status --json`, **Then** a saída indica estado "desconectado", sem sessão ativa.
2. **Given** uma VPN conectada a um perfil (iniciada pela GUI ou por um `connect` anterior via CLI), **When** um processo externo roda `openfortivpn-gui status --json`, **Then** a saída indica estado "conectado", o nome do perfil e o tempo decorrido desde o início da conexão.
3. **Given** a GUI aberta e mostrando "conectando" (processo `openfortivpn` subindo), **When** o status é consultado via CLI, **Then** a saída reflete "conectando", consistente com o que a GUI mostra no mesmo instante.

---

### User Story 2 - Conectar a um perfil por fora (Priority: P2)

Um processo externo precisa disparar a conexão a um perfil de VPN já cadastrado, sem precisar abrir a janela gráfica nem simular cliques.

**Why this priority**: Depende do estado de leitura (US1) para ter sentido — só depois de saber que não há conexão ativa é que faz sentido conectar. É a segunda ação mais valiosa (automatizar o "ligar a VPN" a partir de outro fluxo, ex. um script de início de expediente).

**Independent Test**: Pode ser testado sozinho rodando `openfortivpn-gui connect <perfil>` com a VPN desconectada e um perfil válido, e confirmando (via `status` ou observação do sistema) que a conexão sobe com o mesmo comportamento de quando disparada pela GUI.

**Acceptance Scenarios**:

1. **Given** a VPN desconectada e um perfil válido cadastrado, **When** um processo externo roda `openfortivpn-gui connect <perfil>`, **Then** a conexão é iniciada com esse perfil, com o mesmo comportamento (processo `sudo -n openfortivpn`, diagnóstico de falha) já usado pela GUI.
2. **Given** um nome de perfil que não existe, **When** `connect <perfil>` é chamado, **Then** o comando falha com mensagem clara e código de saída diferente de zero, sem tentar iniciar nenhum processo.
3. **Given** já existe uma conexão ativa (iniciada pela GUI ou por outro `connect`), **When** `connect <perfil>` é chamado novamente, **Then** o comando recusa a nova tentativa com mensagem clara, sem derrubar a conexão existente nem iniciar um segundo processo `openfortivpn`.

---

### User Story 3 - Desconectar por fora (Priority: P3)

Um processo externo precisa encerrar a conexão VPN ativa, tenha ela sido iniciada pela GUI ou por um `connect` via CLI em outro momento (inclusive em outro processo).

**Why this priority**: É a ação de menor frequência esperada de uso automatizado (a motivação principal do Farol é consultar status; conectar/desconectar por fora é um bônus), mas fecha o ciclo completo de controle programático.

**Independent Test**: Pode ser testado sozinho conectando a VPN (via GUI ou via `connect`), depois rodando `openfortivpn-gui disconnect` num processo separado, e confirmando via `status` que a conexão caiu.

**Acceptance Scenarios**:

1. **Given** uma conexão ativa iniciada pela GUI, **When** um processo externo roda `openfortivpn-gui disconnect`, **Then** a conexão é encerrada, com o mesmo comportamento de quando o botão "Desconectar" é usado na GUI.
2. **Given** nenhuma conexão ativa, **When** `disconnect` é chamado, **Then** o comando informa que não há nada para desconectar, com código de saída diferente de zero, sem tentar matar nenhum processo do sistema.

---

### Edge Cases

- O que acontece quando `status --json` é chamado logo após o sistema reiniciar, sem a GUI ter sido aberta ainda nesta sessão? Deve refletir corretamente "desconectado" (ou "conectado", se a VPN tiver sido deixada ativa por fora).
- O que acontece quando `connect` é chamado com o mesmo perfil que já está conectado? Deve ser tratado como o caso "já existe uma conexão ativa" (US2, cenário 3), não como uma reconexão silenciosa.
- O que acontece quando `disconnect` é chamado por um processo diferente do que originou o `connect` (ex.: GUI conectou, um script externo desconecta; ou um `connect` via CLI seguido de `disconnect` via CLI em invocação separada)? Deve encerrar a conexão real do sistema de forma confiável, independentemente de qual processo a originou.
- O que acontece se a regra de `sudo -n` não permitir a operação sem senha (mesma limitação já documentada para a GUI)? O comando `connect`/`disconnect` deve reportar a falha de forma clara via código de saída e mensagem, sem travar esperando senha interativa.
- O que acontece se dois comandos (`connect` e `disconnect`, ou dois `connect` para perfis diferentes) forem disparados quase simultaneamente por processos externos distintos? Não deve haver corrupção do arquivo de estado nem dois processos `openfortivpn` concorrentes sem que um deles seja reportado como falha clara.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST expor um comando `status` que informa o estado atual da conexão (desconectado / conectando / conectado), o perfil selecionado e a lista de perfis disponíveis, com uma opção de saída em formato estruturado (`--json`) pensada para consumo por outro programa.
- **FR-002**: Quando conectado, a saída de `status` MUST incluir o nome do perfil ativo e o tempo decorrido desde o início da conexão.
- **FR-003**: O sistema MUST expor um comando `connect <perfil>` que inicia a conexão ao perfil informado, reaproveitando a mesma lógica de conexão (e os mesmos diagnósticos de falha) já usados pela interface gráfica — sem duplicar essa regra de negócio. O comando MUST bloquear até confirmar que a conexão subiu (com um timeout configurável/padrão razoável) e só então retornar sucesso ou falha — um script chamador deve conseguir saber o resultado de uma única invocação, sem precisar de uma segunda chamada de `status` para confirmar.
- **FR-004**: O sistema MUST expor um comando `disconnect` que encerra a conexão ativa, reaproveitando a mesma lógica já usada pela interface gráfica.
- **FR-005**: `connect` MUST recusar iniciar uma nova conexão quando já existe uma ativa, com mensagem e código de saída que deixem isso explícito para quem chamou.
- **FR-006**: `disconnect` MUST informar de forma explícita (mensagem e código de saída diferente de zero) quando não há nenhuma conexão ativa para encerrar.
- **FR-007**: `connect <perfil>` MUST validar que o perfil informado existe antes de tentar conectar, informando erro claro (e código de saída diferente de zero) quando não existir.
- **FR-008**: Todos os comandos MUST refletir o estado real do processo `openfortivpn` em execução no sistema no momento da chamada — não um valor em cache que possa estar desatualizado — funcionando corretamente tanto com a GUI aberta quanto fechada.
- **FR-009**: O formato de saída de `status --json` MUST ser estável e documentado (nomes de campos e valores possíveis), para que um consumidor externo (ex.: o Farol) possa integrar sem inspecionar o código-fonte deste projeto. Estado e códigos de erro estruturados MUST ficar em inglês/snake_case estável — é neles que o consumidor programático se baseia; qualquer mensagem legível para humano incluída na saída (ex.: campo `message`) fica em português (Princípio IV da constitution do projeto), mas serve apenas para exibição — MUST NOT ser a única forma de o consumidor identificar o que aconteceu.
- **FR-010**: `disconnect` MUST encerrar de forma confiável a conexão real do sistema mesmo quando chamado por um processo diferente daquele que originou o `connect` (GUI ou outra invocação de CLI), reaproveitando o fallback já existente de encerrar o processo pelo nome (`pkill -x openfortivpn`) — não é requisito desta feature localizar e usar o PID exato salvo em disco (decisão de escopo: a correção de precisão do mecanismo de reattach fica fora desta feature).

### Key Entities

- **Estado de conexão**: um de três valores (desconectado, conectando, conectado) — já existente internamente, apenas exposto por um novo canal.
- **Sessão ativa**: perfil em uso, tempo decorrido, interface de rede associada — já existente internamente, apenas exposto por um novo canal.
- **Perfil VPN**: nome e caminho de um perfil de conexão já cadastrado (administrado ou criado pela GUI) — entidade já existente, apenas consultada/referenciada pela CLI, não criada por ela.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um processo externo consegue determinar corretamente o estado da VPN (desconectado/conectando/conectado) em 100% das consultas via `status --json`, incluindo nos casos em que a GUI não está aberta.
- **SC-002**: Um script de automação consegue conectar a um perfil válido e confirmar (via `status`) que a conexão subiu, sem qualquer interação manual, em uma única chamada de `connect`.
- **SC-003**: Um script de automação consegue encerrar uma conexão ativa — independentemente de ter sido iniciada pela GUI ou por um `connect` anterior via CLI — com uma única chamada de `disconnect`, sem deixar o processo `openfortivpn` órfão no sistema.
- **SC-004**: Tentativas inválidas (`connect` com perfil inexistente, `connect` com conexão já ativa, `disconnect` sem conexão ativa) são identificáveis programaticamente pelo código de saída do comando, sem exigir que o script chamador faça parsing de texto livre.

## Assumptions

- A CLI roda no mesmo usuário do sistema operacional que hoje executa a GUI, com a mesma configuração de `sudo -n` já usada por ela — não há requisito novo de autenticação ou multiusuário.
- Não há requisito de suportar múltiplos consumidores externos disparando comandos concorrentes de forma coordenada entre si — cada chamada é tratada de forma independente, e condições de corrida (ver Edge Cases) devem falhar de forma segura e reportável, não silenciosamente.
- O contrato de campos de `status --json` (nomes e formatos) é uma decisão a fechar no plano técnico; esta especificação define apenas o conteúdo mínimo obrigatório (estado, perfil, perfis disponíveis, dados de sessão quando conectado).
- A criação/edição de perfis de VPN continua exclusiva da GUI (issue #7, já implementada) — esta feature não adiciona um comando de CLI para gerenciar perfis, apenas para consultá-los e usá-los.
- `connect` bloqueia até confirmar a subida da conexão, usando um timeout padrão razoável (a decidir no plano técnico, ex.: alguns segundos, consistente com o intervalo de `tick()` já usado internamente); esgotado o timeout sem confirmação, o comando falha com mensagem clara, sem deixar de reportar caso o processo suba depois por conta própria (quem chamou pode confirmar com `status`).
- `disconnect` cross-processo usa o mesmo fallback "matar por nome" (`pkill -x openfortivpn`) já documentado para o caso de reattach da GUI — não há requisito nesta feature de tornar esse mecanismo mais preciso por PID.
