<!--
Sync Impact Report
- Version change: (template não ratificado) → 1.0.0 (criação inicial)
- Bump rationale: MAJOR por convenção de primeira ratificação — não há versão anterior publicada
  para comparar (o arquivo continha apenas os placeholders do template do Spec Kit). A partir desta
  versão, toda mudança segue o versionamento semântico descrito em "## Governance".
- Added sections:
  - "## Core Principles" (6 princípios, derivados de decisões arquiteturais já reais e
    documentadas em AGENTS.md: camadas desacopladas via contratos ABC, sudo não-interativo,
    perfis administrados somente-leitura, interface em PT-BR, testes por contrato, sem build step).
  - "## Stack e Estrutura do Projeto".
  - "## Fluxo de Desenvolvimento com Spec Kit".
  - "## Governance", com o mesmo padrão de regras do projeto irmão Farol
    (/home/samueldias/dev/pessoal/scripts/farol/.specify/memory/constitution.md): Emendas,
    Versionamento semântico dedicado, Revisão de conformidade e — regra pedida explicitamente
    pelo usuário nesta sessão — Dívida técnica rastreável via issue no GitHub, nunca só em
    comentário de código ou nota de sessão.
- Modified principles: nenhum (primeira versão).
- Removed sections: nenhuma.
- Templates requiring follow-up: nenhum.
- Deferred / TODO placeholders: nenhum.
-->

# openfortivpn-gui Constitution

## Core Principles

### I. Camadas Desacopladas via Contratos ABC

O `VpnController` (`controller/vpn_controller.py`) é uma máquina de estados pura e MUST NOT
depender de GTK ou de qualquer outra biblioteca de UI, direta ou indiretamente. Toda dependência
externa do controller (processo de VPN, detecção de interface de rede, fonte de perfis, escrita de
perfis, ícone por perfil, persistência de estado e histórico) MUST ser expressa como um contrato
ABC em `core/interfaces/`, implementado concretamente em `services/`. Somente o pacote `ui/`
importa `gi`/`Gtk`/`AppIndicator3`.

**Rationale**: isolar a regra de negócio (estados de conexão, transições, diagnóstico de falha) de
qualquer toolkit gráfico é o que torna o controller testável sem display e reutilizável por
qualquer novo consumidor — incluindo um modo CLI headless — sem duplicar lógica.

### II. Sudo Não-Interativo, Nunca Pede Senha

Toda operação privilegiada (iniciar/encerrar o processo `openfortivpn`) MUST usar `sudo -n`
(não interativo). O aplicativo MUST NOT bloquear esperando senha em terminal. Se a regra de sudo
do sistema não permitir a operação sem senha, a falha é esperada, silenciosa no momento da
chamada, e percebida no ciclo de verificação seguinte (`tick()`), nunca por um prompt bloqueante.

**Rationale**: é uma GUI de bandeja de uso contínuo, não uma sessão de terminal interativa — travar
esperando input de senha derrubaria a responsividade da aplicação inteira (single-thread GTK).

### III. Perfis Administrados são Somente-Leitura; Escrita Isolada no Diretório do Usuário

Perfis de VPN administrados em `/etc/openfortivpn/` MUST NUNCA ser escritos, movidos ou renomeados
pela GUI — apenas lidos. Qualquer perfil criado ou editado pela própria aplicação MUST ser
persistido exclusivamente em `~/.config/openfortivpn-gui/profiles/`, nunca em `/etc/openfortivpn/`.
Em colisão de nome entre as duas fontes, o perfil administrado tem prioridade.

**Rationale**: escrever em `/etc` exigiria privilégio elevado interativo (fora do modelo de sudo
não interativo do Princípio II) e criaria risco de corromper configuração gerenciada pelo sistema
ou por outra ferramenta administrativa.

### IV. Interface em Português (PT-BR)

Toda mensagem de UI, notificação e texto voltado ao usuário final MUST ser escrita em português —
o público deste aplicativo é PT-BR. Identificadores de código, comentários técnicos e documentação
voltada a quem desenvolve (`AGENTS.md`, artefatos do Spec Kit) seguem a convenção normal de código
em inglês/português conforme já usada no repositório, sem essa obrigação.

**Rationale**: é uma decisão de produto já estabelecida e consistente em toda a base de código
existente — inconsistência de idioma na UI degradaria a experiência do único público-alvo do
aplicativo.

### V. Testes por Contrato, Não por Framework de UI

`core/models/`, `services/` e `controller/` MUST ter cobertura de teste automatizado via
`pytest`, usando fakes/dublês que implementam os contratos ABC de `core/interfaces/` — nunca
mockando GTK ou dependendo de display. A camada `ui/` (GTK/AppIndicator) MUST NOT ser cobrada por
teste automatizado que dependa de renderização gráfica real; sua validação é por smoke test manual
(`dev/render_smoke.sh`) contra um `Xvfb`.

**Rationale**: testar contra os contratos, não contra GTK, é a consequência direta do Princípio I —
mantém a suíte rápida, determinística e executável em CI sem display, e concentra o valor do teste
automatizado onde a regra de negócio de fato vive.

### VI. Sem Build Step

O aplicativo MUST permanecer executável diretamente via shebang Python (`#!/usr/bin/env python3`),
sem etapa de compilação, empacotamento ou transpilação antes de rodar. Novas dependências de
runtime via `pip` MUST ser adicionadas apenas quando estritamente necessárias — GTK3/AppIndicator3/
PyGObject continuam resolvidos pelo sistema operacional, não pelo `requirements.txt`.

**Rationale**: é um script pessoal instalado via symlink em `~/.local/bin/`; introduzir um build
step aumentaria o atrito de instalação e manutenção sem benefício proporcional para um projeto
deste porte.

## Stack e Estrutura do Projeto

Python 3 + GTK3 (via PyGObject) + AppIndicator3, sem framework de aplicação além do próprio
`Gtk.Application`. Arquitetura em camadas: `core/interfaces` (contratos) → `services` (implementação
concreta) → `controller` (máquina de estados) → `ui` (GTK/AppIndicator), conforme documentado em
`AGENTS.md`. Persistência local em `~/.config/openfortivpn-gui/` (perfis, estado, histórico,
ícones) e `$XDG_RUNTIME_DIR/openfortivpn-gui/` (log e marcador de sessão ativa). Suíte de testes
com `pytest` (`requirements/dev.txt`); sem dependência de runtime via `pip` além da stdlib por
padrão.

## Fluxo de Desenvolvimento com Spec Kit

Este projeto usa o Spec Kit (`.specify/`) para features não triviais: `/speckit-specify` →
`/speckit-clarify` (quando houver ambiguidade real) → `/speckit-plan` → `/speckit-tasks` →
`/speckit-implement`. `AGENTS.md`, na raiz do repositório, continua sendo a referência viva de
arquitetura e convenções para quem já trabalha no código — deve ser mantido atualizado a cada
mudança relevante, independentemente do Spec Kit ter sido usado ou não para chegar a ela.

## Governance

Esta constitution tem precedência sobre qualquer prática, template ou convenção de código deste
projeto que a contradiga. Em caso de conflito entre esta constitution e outro documento do
repositório (incluindo `AGENTS.md`), esta constitution prevalece até que seja formalmente emendada
— e o conflito MUST ser sinalizado a quem estiver conduzindo o trabalho, para reconciliação.

- **Emendas**: qualquer mudança nesta constitution (adição, remoção ou redefinição de princípio, ou
  mudança de seção de governança) é uma emenda e PRECISA vir acompanhada de justificativa
  registrada no Sync Impact Report no topo deste arquivo.
- **Versionamento**: esta constitution segue versionamento semântico dedicado
  (MAJOR.MINOR.PATCH):
  - MAJOR: remoção ou redefinição incompatível de um princípio existente.
  - MINOR: adição de novo princípio ou expansão material de uma seção existente.
  - PATCH: esclarecimento de redação, correção de erro, refinamento não semântico.
- **Revisão de conformidade**: features, planos e tasks gerados pelo Spec Kit para este projeto
  DEVEM ser verificados contra os princípios acima antes de serem considerados prontos para
  implementação; qualquer desvio precisa de justificativa explícita no artefato correspondente
  (spec, plano ou task), não de exceção silenciosa.
- **Dívida técnica rastreável**: dívida técnica identificada durante o desenvolvimento e
  deliberadamente deixada sem correção imediata (ex.: workaround documentado em comentário,
  decisão consciente de adiar um ajuste, limitação conhecida de uma dependência) MUST ser
  registrada como issue no tracker do projeto (GitHub Issues) antes de a mudança correspondente ser
  considerada concluída. Comentário de código ou nota de sessão, isoladamente, NÃO substituem o
  registro rastreável. Rationale: dívida técnica que existe só em comentário ou em memória de
  sessão desaparece do radar do projeto assim que a sessão termina ou o comentário para de ser
  lido; uma issue no tracker é o único registro que sobrevive à sessão que a criou e que pode
  entrar em backlog, milestone ou priorização futura.
- **README como fonte de verdade externa, mantido atualizado**: o `README.md` é o documento
  voltado para quem chega ao projeto de fora — instalação, uso, status atual. MUST ser atualizado
  sempre que uma mudança de sessão alterar seu conteúdo de forma material (novo modo de uso, ex.:
  a futura CLI da issue #8; mudança relevante de instalação ou requisitos).

**Version**: 1.0.0 | **Ratified**: 2026-09-02 | **Last Amended**: 2026-09-02
