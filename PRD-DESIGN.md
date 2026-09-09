# PRD — Implementação do Design do SPA

**Produto:** Sistema de Gestão de Documentos e Assinaturas (ver [PRD.md](PRD.md))
**Módulo:** Camada de interface do SPA Angular
**Versão:** 1.1 — alinhada à constituição v1.1.0 (Princípios VIII–XI)
**Data:** 08/09/2026
**Status:** Pronto para implementação
**Referência visual:** [canvas publicado](https://claude.ai/code/artifact/752f8469-848c-4255-957e-07b973f22f6d) · fontes em [design/](design/)

---

## 0. Enquadramento

Este documento cobre **apenas a camada de interface** do SPA. O backend, o contrato da API,
o modelo de dados e as regras de negócio estão fechados e implementados — nada aqui os
altera. O que se constrói é o sistema visual, os componentes de UI e a reescrita dos
templates das cinco telas existentes.

Três coisas que este PRD assume como já resolvidas e que não devem ser reabertas:

- O contrato da API é o de [`contracts/rest-api.md`](specs/001-document-signature-management/contracts/rest-api.md). Nenhum campo novo é pedido ao backend.
- Os serviços TypeScript em `frontend/src/app/core/api/` já cobrem tudo que as telas
  precisam, incluindo filtros (`DocumentService.list(filters)`) e paginação
  (`Paginated<T>` traz `count`, `next`, `previous`).
- Os modelos em `frontend/src/app/core/models/` são a fonte da verdade sobre formatos.

## 1. Contexto e problema

O SPA funciona: 74 testes passando, 86% de cobertura, todas as rotas guardadas, todos os
estados de erro tratados. O que não existe é **qualquer camada visual**. Concretamente:

| Evidência | Estado hoje |
|---|---|
| `frontend/src/styles.scss` | vazio (só o comentário gerado pelo CLI) |
| `frontend/src/app/app.component.scss` | 0 bytes |
| SCSS por componente | nenhum arquivo existe |
| `frontend/src/index.html` | `<html lang="en">`, `<title>Frontend</title>` |
| Fontes | nenhuma carregada — o navegador escolhe |
| Textos da interface | inglês (`Documents`, `Sign out`, `No documents yet.`) |

O resultado é uma aplicação correta que parece um protótipo interno inacabado. Três
consequências reais para quem usa:

1. **Os dois status se confundem.** `provider_status` (nosso hand-off com a ZapSign) e
   `status` (assinatura, reportado por eles) aparecem como duas colunas de texto cru na
   mesma tabela. Ler "submitted" ao lado de "pending" e concluir a coisa errada é o erro
   mais caro que esta interface permite hoje.
2. **Falha não se distingue de risco.** O erro do provedor e o insight de risco da análise
   são o mesmo `<small>` sem tratamento. São problemas de natureza diferente, com donos e
   soluções diferentes.
3. **A densidade é acidental.** Formulário, tabela e detalhe empilhados verticalmente
   empurram a lista para fora da tela assim que o formulário de criação abre.

## 2. Objetivo

Implementar o sistema visual desenhado, de forma que:

- os três vocabulários de status (hand-off, assinatura, análise) sejam visualmente
  inconfundíveis, sem depender só de cor;
- a interface fique legível e densa em desktop, em tema claro e escuro;
- toda a interface fale português do Brasil;
- nada disso exija biblioteca de componentes, framework de CSS ou mudança no backend.

## 3. Escopo

### 3.1 Dentro do escopo

- Sistema de tokens (cor, tipografia, espaçamento, raio, alturas) em CSS custom properties.
- Tema claro e escuro, seguindo `prefers-color-scheme`.
- Fontes IBM Plex Sans e IBM Plex Mono auto-hospedadas.
- Biblioteca de UI em camadas atômicas (átomos, moléculas, organismos): pastilha de
  status, marcador de assinatura, marcador de análise, botões, campos, chips, cartão,
  tabela, estado vazio, banner de erro, diálogo de confirmação.
- Reescrita dos templates das cinco telas + painel de análise + linhas de signatário.
- Tradução completa da interface para pt-BR.
- Comportamento novo que o design pressupõe (seção 8): filtros, paginação, trilho de
  detalhe/formulário, confirmação de exclusão, estado "analisando".
- `index.html`: idioma, título e cor de tema.
- Acessibilidade verificável (seção 10).

### 3.2 Fora do escopo

- Qualquer mudança em `backend/`.
- Layout mobile dedicado. O alvo é desktop; abaixo de 1280 px o layout se adapta sem
  quebrar (seção 9), mas não há desenho de telas para celular.
- Biblioteca de componentes (Angular Material, PrimeNG) ou framework de CSS (Tailwind).
- Internacionalização de verdade (`@angular/localize`, arquivos de tradução). O pt-BR entra
  como texto literal nos templates.
- Animações além de transições de estado de 120–160 ms.

### 3.3 Bônus (desejável, não obrigatório)

- Botão de alternância manual de tema no cabeçalho, gravando a escolha em `localStorage` e
  aplicando `data-theme` no elemento raiz.
- Contador de alertas no item de navegação, alimentado por `GET /api/alerts/`.
- Ordenação da tabela de documentos por coluna.

## 4. Referência de design

O canvas tem 12 pranchas em três páginas:

| Página | Pranchas |
|---|---|
| Telas | Login · Documentos (principal) · Documentos vazio + criação · Análise (4 estados) · Organização · Relatórios · Alertas · Alertas vazio · Tema escuro |
| Sistema visual | tokens claro/escuro, tipografia, os três vocabulários de status, componentes, grade |
| Direções descartadas | Direção B (console lateral) e C (fila de trabalho), em baixa fidelidade |

Os arquivos-fonte estão em `design/*.dc.html`. Onde o canvas e este PRD divergirem, **este
PRD vence** — ele carrega os valores exatos.

## 5. Fundamentos

### 5.1 Tokens de cor

Declarados em `:root`, redefinidos sob `@media (prefers-color-scheme: dark)` com a guarda
`:root:not([data-theme="light"])`, e novamente sob `:root[data-theme="dark"]` para que a
alternância manual (bônus) vença nos dois sentidos.

| Token | Claro | Escuro | Papel |
|---|---|---|---|
| `--paper` | `#FAF9F7` | `#141311` | fundo da página |
| `--surface` | `#FFFFFF` | `#1C1B18` | cartão, tabela, trilho |
| `--surface-2` | `#F3F1ED` | `#23221E` | preenchimento sutil, rodapé de tabela |
| `--ink` | `#1A1917` | `#F0EDE7` | texto primário |
| `--ink-2` | `#5C5852` | `#ADA79E` | texto secundário |
| `--ink-3` | `#8A857D` | `#7C766E` | rótulo, placeholder, metadado |
| `--line` | `#E3E0D9` | `#302E29` | divisória |
| `--line-2` | `#CBC7BE` | `#423F39` | borda de controle |
| `--accent` | `#4B3FA6` | `#A79BF0` | ação principal, seleção, link |
| `--accent-ink` | `#372C86` | `#C7BEFA` | hover do acento |
| `--accent-soft` | `#EEEBFA` | `#272238` | fundo de linha selecionada |
| `--ok-ink` / `--ok-bg` / `--ok-line` | `#1F5F43` / `#E4F0EA` / `#B4D7C6` | `#8FD9B4` / `#14251D` / `#22452F` | `submitted`, `succeeded` |
| `--warn-ink` / `--warn-bg` / `--warn-line` | `#7A5312` / `#FBF0DC` / `#E9D2A2` | `#E8C078` / `#2A2013` / `#4A3A1D` | risco no conteúdo |
| `--bad-ink` / `--bad-bg` / `--bad-line` | `#8C2B22` / `#FBE9E6` / `#EFC1B8` | `#F0A79A` / `#2B1815` / `#4C2721` | falha do sistema |
| `--mut-ink` / `--mut-bg` / `--mut-line` | `#5C5852` / `#EDEBE6` / `#D8D4CB` | `#ADA79E` / `#23221E` / `#37342F` | `pending_integration`, sem estado |

Preenchimentos de barra dos relatórios (idênticos nos dois temas, validados a ≥ 3:1 contra
a superfície): verde `#2E7D5B`, cinza `#8C857B`, vermelho `#B4483C`, ocre `#A9741F`.
Pontos do marcador de assinatura: assinado `#3E8C68` (escuro `#5FBF91`), recusado `#B4483C`
(escuro `#D9776A`), pendente = contorno de `--line-2` sem preenchimento.

**Regra:** nenhuma cor pode ter sua única definição dentro de um bloco `@media` ou
`[data-theme]`. Toda cor nasce em `:root` e é *redefinida* no escuro.

### 5.2 Tipografia

Duas famílias, com papéis separados e não negociáveis:

- **IBM Plex Sans** (400, 500, 600) — tudo que uma pessoa escreveu: rótulos, títulos, copy,
  nomes de documento, mensagens.
- **IBM Plex Mono** (400, 500) — tudo que a máquina escreveu: valores de status, UUIDs,
  tokens, contagens, datas, códigos de erro, rótulos de seção em versalete.

A troca de família é o sinal de procedência. Não usar mono por estética.

| Papel | Tamanho / peso | Observação |
|---|---|---|
| Título de página | 27 / 600 | `letter-spacing: -0.02em` |
| Título de seção | 20 / 600 | `-0.012em` |
| Título de painel | 15 / 600 | |
| Nome de documento | 13 / 600 | |
| Corpo | 12.5 / 400 | `line-height: 1.5` |
| Apoio / legenda | 11.5 / 400 | cor `--ink-2` ou `--ink-3` |
| Rótulo de seção (`.eyebrow`) | 10 / 500 mono | versalete, `letter-spacing: .13em` |
| Valor técnico | 11–11.5 mono | UUID, token, status, data |
| Número herói | 34 / 500 mono | tiles de relatório, `-0.02em` |

Corpo base do `<body>`: `400 13px/1.5`. Aplicar `text-wrap: pretty` em blocos de texto.

### 5.3 Grade, raio e alturas

| Dimensão | Valores |
|---|---|
| Espaçamento | 4 · 8 · 14 · 20 · 24 · 32 |
| Raio | 3 (pastilha) · 4 (controle) · 6 (cartão) |
| Borda | 1 px sempre; nunca hairline abaixo de 1 px |
| Alturas | 22 pastilha · 26 botão compacto · 32 botão/select · 34 campo · 44 mínimo de linha de tabela |
| Trilho de detalhe | 452 px fixo |
| Padding de página | 22 px vertical · 24 px horizontal |
| Sombra | nenhuma, exceto o anel de foco |

### 5.4 Fontes — decisão fechada

As fontes são **auto-hospedadas**, não carregadas do Google Fonts. Motivo: o README garante
que a stack inteira sobe e roda sem rede (`ZAPSIGN_USE_FAKE=true`, provider de IA com
fallback local); uma dependência de `fonts.googleapis.com` quebraria essa promessa e
adicionaria um terceiro ao caminho de renderização.

Implementação: instalar `@fontsource/ibm-plex-sans` e `@fontsource/ibm-plex-mono`,
importar apenas os pesos e o subconjunto `latin` usados, e declarar `font-display: swap`.
Se a variante variável estiver disponível nos pacotes, preferi-la e reduzir a um arquivo
por família. Fallback obrigatório em toda declaração:

```scss
--font-sans: "IBM Plex Sans", system-ui, "Segoe UI", sans-serif;
--font-mono: "IBM Plex Mono", ui-monospace, "SFMono-Regular", monospace;
```

## 6. Vocabulário de status — regra normativa

A regra que organiza a interface inteira. Cada uma das três escalas tem **forma própria**, e
nenhuma depende só de cor.

| Escala | Campo | Forma | Valores |
|---|---|---|---|
| **Hand-off** (nosso) | `provider_status` | pastilha com fundo, borda de 1 px e ícone | `pending_integration` (neutro, círculo tracejado) · `submitted` (verde, check) · `failed` (vermelho, ×) |
| **Assinatura** (deles) | `status` | ponto de 7 px + texto em versalete mono, **sem** pastilha | preenchido verde = assinado · preenchido vermelho = recusado · contorno = pendente · `—` = sem status |
| **Análise** | `latest_analysis` | ícone + texto, sem pastilha | triângulo ocre = risco · círculo vermelho = falhou · check cinza = sem risco · `—` = nunca analisado |

Justificativa das formas, para não se perderem na implementação:

- Só o hand-off ganha pastilha porque é o único estado que **nós** controlamos e o único
  com ação de recuperação (`/resync/`).
- Assinatura é leitura de terceiro; `status` é texto livre e um valor novo que a ZapSign
  invente precisa renderizar de forma sensata — o ponto neutro é o padrão.
- Risco (ocre) é achado **sobre o contrato**; falha (vermelho) é problema **do sistema**.
  Nunca a mesma cor, nunca o mesmo ícone, nem quando aparecem na mesma linha.

Ícones são SVG inline, traçado, grade de 12 px, `stroke-width` 1.3–1.7, `currentColor`.
**Emoji é proibido** em qualquer lugar da interface.

## 7. Camadas e componentes a construir

A composição segue o **Princípio XI** da constituição — Atomic Design com **direção de
importação de mão única**: átomo → molécula → organismo → página, nunca o contrário.
Cada elemento vive na camada mais baixa que suas dependências permitem; promover algo
por conveniência de local é defeito, tanto quanto uma camada baixa que alcança para
cima atrás de um serviço ou do estado de uma página.

| Camada | Pode depender de | Não pode |
|---|---|---|
| Átomo | tokens e nada mais | modelo de domínio, serviço, HTTP |
| Molécula | tipos de `core/models/` | serviço, HTTP, estado de página |
| Organismo | moléculas, átomos, serviços de `core/api/` | estado interno de outra página |
| Página | organismos | markup que caiba numa camada abaixo |

Peças reutilizáveis ficam em `frontend/src/app/ui/{atoms,molecules,organisms}/`. Um
organismo usado por uma tela só permanece na pasta da feature. `core/` guarda modelos,
serviços e guards, e não pertence a nenhuma camada visual.

### 7.1 Átomos

Regra herdada do Princípio VIII: átomo **sem** comportamento e **sem** semântica
própria é classe SCSS global, não componente — é o que impede o orçamento de 4 kB por
componente de ser gasto em duplicação.

| Átomo | Forma | Por quê |
|---|---|---|
| `.badge` `.btn` `.inp` `.sel` `.chip` `.card` `.kv` `.eyebrow` | classe SCSS global | sem comportamento e sem semântica própria |
| `EmptyStateComponent` | componente | projeta conteúdo e tem semântica de região |
| `ConfirmDialogComponent` | componente | tem comportamento e foco preso, mas não conhece domínio algum — por isso é átomo, não organismo |
| `ProgressStepComponent` | componente | etapa + barra do estado "analisando" |

### 7.2 Moléculas

Um átomo ligado a **um** valor de domínio. Importam de `core/models/`; nenhuma injeta
serviço nem busca dado.

| Molécula | Entrada | Onde é usada |
|---|---|---|
| `ProviderStatusBadgeComponent` | `status: ProviderStatus` | tabela, trilho, alertas, relatórios |
| `SignatureStatusComponent` | `status: string \| null` | tabela, trilho, lista de signatários, relatórios |
| `AnalysisMarkerComponent` | `analysis: DocumentAnalysis \| null` | tabela de documentos |
| `ErrorMessageComponent` | `error: ApiError \| null` | **existente**, sai de `shared/` para `ui/molecules/` |
| `InsightItemComponent` | `insight: Insight` | painel de análise |
| `AnalysisRunItemComponent` | `run: DocumentAnalysis` | histórico de análises |

### 7.3 Organismos

Regiões autocontidas de tela. Podem ter estado local e injetar serviços.

| Organismo | Local | Observação |
|---|---|---|
| `AppHeaderComponent` | `ui/organisms/` | usado por toda a aplicação |
| `DocumentsTableComponent` | `documents/` | específico da feature |
| `DocumentDetailRailComponent` | `documents/` | detalhe + painel de análise |
| `DocumentFormComponent` | `documents/` | criação e edição, no mesmo trilho |
| `AnalysisPanelComponent` | `documents/` | **existente**, reescrito com os quatro estados |
| `SignerRowsComponent` | `signers/` | **existente**; possui a estrutura do `FormArray` |
| `CompanyFormComponent` | `companies/` | inclui o bloco de segredo do token |
| `ReportTilesComponent`, `ReportDistributionComponent` | `reports/` | números herói e barras |
| `AlertGroupComponent` | `alerts/` | um por grupo (parados, risco) |

### 7.4 Páginas

Os componentes roteados que já existem — `login`, `documents`, `companies`, `reports`,
`alerts`. Depois do refactor eles ficam com rota, busca de dados e orquestração, e
delegam a renderização aos organismos. Markup que couber numa camada abaixo não fica
na página.

### 7.5 Nota sobre o `ErrorMessageComponent`

Hoje despeja `err.detail` e um `<ul>` de `err.fields`, e vive em `shared/`. A versão
nova mantém a mesma API (`input<ApiError | null>`), muda de lugar para
`ui/molecules/`, e passa a renderizar: ícone, mensagem em `--bad-ink`, código técnico
(`err.code`) em mono pequeno, e os erros por campo associados ao campo correspondente
via `aria-describedby` — não mais numa lista solta no topo. A pasta `shared/` deixa de
existir.

## 8. Telas — o que muda em cada uma

Cada item marcado **[novo]** é comportamento que não existe hoje, não apenas estilo. Estão
agrupados na Fase 4 (seção 14) para poderem ser cortados sem afetar o resto.

### 8.1 Login (`core/auth/login.component.ts`)

Divisão em duas colunas: painel escuro de 520 px à esquerda com a proposta do produto e a
legenda do ciclo de envio; formulário à direita. Erro de credencial vira banner com
`detail` + `code`. O template inline sai para `login.component.html`.

### 8.2 Documentos (`documents/`) — a tela principal

Reorganização estrutural: **lista fluida à esquerda, trilho de 452 px à direita**. O trilho
tem três modos mutuamente exclusivos — vazio, detalhe do documento selecionado, ou
formulário de criação/edição. Hoje `selected` e `editingId` são sinais independentes e o
formulário fica acima da lista; passa a existir um modo derivado:

```ts
readonly railMode = computed<'none' | 'detail' | 'form'>(...)
```

- Célula do documento: nome em 13/600, e abaixo, em mono 10.5, organização · referência
  externa · data de criação.
- Colunas: Documento (fluida) · Hand-off (178) · Assinatura (136) · Signatários (92) ·
  Análise (104) · ações (88).
- Erro do provedor (`last_provider_error`) renderiza dentro da célula do documento, com
  ícone, em `--bad-ink`, com o texto explicando que o documento está salvo.
- Ação "Reenviar" (hoje "Resync") aparece só quando `canResync()` — o restante das ações vai
  para um botão de reticências.
- **[novo]** Linha de filtros: hand-off, assinatura e organização. `DocumentService.list()`
  já aceita `DocumentFilters`; hoje é chamado sem argumento.
- **[novo]** Rodapé de paginação usando `count`/`next`/`previous` do envelope.
- **[novo]** Confirmação antes de excluir. Hoje `remove()` apaga direto, sem perguntar.

### 8.3 Painel de análise (`documents/analysis-panel.component.*`)

Quatro estados, todos desenhados: sucesso, falha, sem análise e **[novo]** em andamento.

- Sucesso: resumo em corpo, tópicos faltantes como chips tracejados, insights em lista —
  o insight com `risk: true` ganha bloco ocre com ícone e o rótulo `RISCO`; os demais são
  itens neutros com ponto. Rodapé com `source` e `model` em mono.
- Falha: pastilha `failed`, o `error_reason` cru em mono, a tradução em português do motivo
  (`no_text`, `unreachable`, `not_pdf`, `too_large`, `timeout`), a garantia de que o
  documento não foi afetado, e o botão de repetir como ação **primária**.
- Histórico: lista de execuções com data, estado, `source` e contagem de riscos; a execução
  atual marcada. Mantém o toggle existente.
- **[novo]** Estado "analisando": o botão fica desabilitado com rótulo "Analisando…", e o
  painel mostra a etapa e o teto de 15 s (`AI_TIMEOUT_SECONDS`). Hoje só existe o rótulo do
  botão.

### 8.4 Organização (`companies/`)

Mesma divisão lista + trilho. O campo de token recebe **tratamento visual de segredo**:
bloco escuro, ícone de cadeado, valor mascarado (`api_token_masked`) em mono, campo vazio
com o texto "deixe em branco para manter o token atual" e a nota de que o valor nunca é
devolvido pela API. A recusa de exclusão (`409 company_has_documents`) vira banner
explicando *por que* foi recusada e o que fazer, não só a mensagem crua.

### 8.5 Relatórios (`reports/`)

De listas `<ul>` para painel: quatro tiles com número herói (total, aguardando assinatura,
falhas no envio, com risco aberto), duas figuras de distribuição em barras horizontais
(hand-off e assinatura) e a lista de riscos recentes.

Regras das barras, herdadas do sistema de dataviz:

- Toda barra tem **rótulo direto** — nome do status e contagem. Cor nunca é o único sinal.
- Trilho em `--surface-2`, preenchimento com raio 4 px só na ponta livre, altura 10 px.
- Ocre (risco) nunca aparece ao lado de vermelho (falha) na mesma figura.
- Sem eixo, sem grade, sem legenda separada — o rótulo direto substitui as três.

### 8.6 Alertas (`alerts/`)

Dois cartões lado a lado: "Documentos parados" e "Achados de risco", cada um com contagem no
cabeçalho e o limite aplicado em mono (`ALERT_STALLED_DAYS`). Cada alerta traz o nome do
documento como link, o detalhe e uma ação. O estado vazio é afirmativo — "nada precisa de
atenção agora" com ícone de check verde — porque é um resultado, não uma ausência de dados.
Manter o texto que explica que um documento pode aparecer nos dois grupos.

### 8.7 Cabeçalho (`app.component.*`)

Marca à esquerda (SVG + nome), navegação com item ativo em `--accent-soft`, usuário e sair à
direita. Altura 56 px, fundo `--surface`, divisória inferior de 1 px. **[novo, bônus]**
contador de alertas no item correspondente.

## 9. Responsividade

O alvo é desktop. Requisitos mínimos:

- Em 1440 px o layout é o desenhado.
- Em 1280 px nada quebra: o trilho mantém 452 px e a lista comprime.
- Abaixo de 1180 px o trilho deixa de ser coluna e passa a sobreposição à direita, com
  fundo esmaecido e fechamento por `Esc` e por clique fora.
- **A página nunca rola na horizontal.** Conteúdo largo (tabelas) rola dentro do próprio
  contêiner com `overflow-x: auto`.

## 10. Acessibilidade

| ID | Requisito |
|---|---|
| A11Y-01 | Contraste AA: 4.5:1 para texto normal, 3:1 para texto ≥ 18.66 px e para bordas de controle, nos **dois** temas |
| A11Y-02 | Status nunca comunicado só por cor — sempre cor + forma + texto |
| A11Y-03 | Foco visível em todo elemento interativo: `outline` de 2 px em `--accent` com 2 px de deslocamento; `:focus-visible`, não `:focus` |
| A11Y-04 | Tabelas com `<th scope="col">`; a coluna de ações tem cabeçalho acessível, não vazio |
| A11Y-05 | Erro de campo associado ao campo por `aria-describedby`; o campo recebe `aria-invalid="true"` |
| A11Y-06 | Banner de erro com `role="alert"` (já existe em `ErrorMessageComponent` e no login) |
| A11Y-07 | Todo botão só com ícone tem `aria-label` |
| A11Y-08 | SVG decorativo com `aria-hidden="true"` |
| A11Y-09 | Trilho em sobreposição prende o foco enquanto aberto e o devolve ao fechar |
| A11Y-10 | Alvo de clique mínimo de 26 × 26 px, com área de toque efetiva de 32 px |

## 11. Idioma — pt-BR

Toda a interface passa a português do Brasil. **Exceção deliberada:** valores técnicos
vindos da API continuam como a API os entrega, em mono — `pending_integration`, `submitted`,
`failed`, `succeeded`, `llm+regex`, `no_text`, `company_has_documents`. Traduzi-los criaria
uma segunda verdade e quebraria a correspondência com os logs e a documentação da API.

Glossário fechado:

| Inglês (hoje) | pt-BR |
|---|---|
| Documents / Organization / Reports / Alerts | Documentos / Organização / Relatórios / Alertas |
| Sign out / Sign in | Sair / Entrar |
| Create and send for signature | Criar e enviar para assinatura |
| Save changes / Cancel / Edit / Delete | Salvar alterações / Cancelar / Editar / Excluir |
| Resync | Reenviar |
| Re-analyze / Analyzing… | Reanalisar / Analisando… |
| Show history / Hide history | Histórico (com estado alternado) |
| Missing topics / Insights | Tópicos faltantes / Insights |
| No documents yet. | Nenhum documento ainda |
| Nothing needs attention right now. | Nada precisa de atenção agora |
| Loading… | Carregando… |
| By hand-off status / By signature status | Por status de hand-off / Por status de assinatura |

Também mudam:

- `frontend/src/index.html`: `lang="pt-BR"`, `<title>Documentos e Assinaturas</title>`, e
  `<meta name="theme-color">` nas duas variantes de tema.
- Datas em `pt-BR` (`DatePipe` com locale registrado em `app.config.ts`) — hoje
  `analysis-panel.component.html` imprime `created_at` cru.

## 12. Organização do código

### 12.1 Estilos

```
frontend/src/
├── styles.scss                 importa os parciais, na ordem abaixo
└── styles/
    ├── _tokens.scss            custom properties, claro + escuro
    ├── _reset.scss             box-sizing, margens, listas, foco
    ├── _typography.scss        @font-face, escala, .mono, .eyebrow
    └── _components.scss        .badge .btn .inp .sel .chip .card .kv, tabela
```

### 12.2 Componentes

```
frontend/src/app/
├── ui/
│   ├── atoms/                  empty-state, confirm-dialog, progress-step
│   ├── molecules/              provider-status-badge, signature-status,
│   │                           analysis-marker, error-message, insight-item,
│   │                           analysis-run-item
│   └── organisms/              app-header
├── documents/                  página + organismos da feature
├── companies/                  página + organismos da feature
├── reports/                    página + organismos da feature
├── alerts/                     página + organismos da feature
├── signers/                    signer-rows (organismo)
└── core/                       modelos, serviços, auth — sem camada visual
```

`shared/` é removida: seu único ocupante, `ErrorMessageComponent`, vira molécula.

### 12.3 Regras

- Os átomos recorrentes ficam **globais** em SCSS, não em SCSS de componente. O
  orçamento `anyComponentStyle` do projeto é **4 kB de aviso e 8 kB de erro**
  (`angular.json`); repetir botão e pastilha por componente estoura isso e duplica CSS.
- O SCSS por componente carrega **só o layout daquela camada** e usa `var(--token)`.
  Custom properties são globais: não é preciso importar nada.
- Nenhum valor de cor, tamanho ou espaçamento literal fora de `_tokens.scss`. As únicas
  exceções permitidas são os preenchimentos de barra da seção 5.1 e os traçados dentro
  de SVG inline.
- Layout com `flex`/`grid` + `gap`. Não espaçar irmãos com margem individual.
- **Nenhum import de baixo para cima.** Um átomo que importa de `core/api/`, ou uma
  molécula que injeta um serviço, é defeito — não questão de gosto.

## 13. Requisitos

### 13.1 Funcionais

| ID | Requisito |
|---|---|
| RF-D-001 | Todos os tokens da seção 5.1 declarados em `:root`, com redefinição para tema escuro nas três formas descritas |
| RF-D-002 | IBM Plex Sans e Mono auto-hospedadas, com `font-display: swap` e stack de fallback |
| RF-D-003 | `provider_status` renderizado como pastilha com ícone, com as três variantes |
| RF-D-004 | `status` de assinatura renderizado como ponto + versalete, jamais como pastilha |
| RF-D-005 | Estado da análise renderizado como ícone + texto, com risco em ocre e falha em vermelho |
| RF-D-006 | Documentos: lista fluida + trilho de 452 px com três modos (vazio, detalhe, formulário) |
| RF-D-007 | Linha selecionada com fundo `--accent-soft` e filete de 2 px em `--accent` na primeira célula |
| RF-D-008 | `last_provider_error` exibido na célula do documento, com ícone e texto explicando que o documento está preservado |
| RF-D-009 | Filtros por `provider_status`, `status` e `company`, passados a `DocumentService.list()` |
| RF-D-010 | Paginação a partir de `count`/`next`/`previous` |
| RF-D-011 | Exclusão de documento e de organização exige confirmação explícita |
| RF-D-012 | Painel de análise nos quatro estados, incluindo "analisando" |
| RF-D-013 | Motivo de falha da análise exibido cru (mono) **e** traduzido |
| RF-D-014 | Histórico de análises com data, estado, `source` e contagem de riscos, com a execução atual marcada |
| RF-D-015 | Campo de token da ZapSign com tratamento de segredo e o texto de "manter o token atual" na edição |
| RF-D-016 | `409 company_has_documents` exibido com causa e caminho de saída |
| RF-D-017 | Relatórios com quatro tiles, duas distribuições em barra com rótulo direto e a lista de riscos recentes |
| RF-D-018 | Alertas em dois grupos, com contagem, limite de dias visível e ação por item |
| RF-D-019 | Estados vazios desenhados em documentos, alertas e organização |
| RF-D-020 | Toda a interface em pt-BR, preservando os valores técnicos da API em inglês/mono |
| RF-D-021 | Datas formatadas em pt-BR |
| RF-D-022 | `index.html` com `lang="pt-BR"`, título e `theme-color` |
| RF-D-023 | Trilho vira sobreposição abaixo de 1180 px, com foco preso e fechamento por `Esc` |
| RF-D-024 | Todos os `data-testid` existentes preservados nos elementos equivalentes |
| RF-D-025 | Componentes organizados nas camadas atômicas da seção 7, com direção de importação de mão única |
| RF-D-026 | Átomo sem comportamento e sem semântica própria implementado como classe SCSS global, não como componente |
| RF-D-027 | `shared/` removida; `ErrorMessageComponent` movido para `ui/molecules/` |

### 13.2 Não funcionais

| ID | Requisito |
|---|---|
| RNF-D-001 | Nenhuma dependência nova de UI: sem biblioteca de componentes, sem framework de CSS, sem biblioteca de ícones |
| RNF-D-002 | Nenhuma requisição a terceiros em tempo de execução; a aplicação continua funcionando sem rede externa |
| RNF-D-003 | Orçamento `anyComponentStyle` respeitado: nenhum SCSS de componente acima de 4 kB |
| RNF-D-004 | Bundle inicial abaixo do aviso de 500 kB configurado |
| RNF-D-005 | `npm run lint`, `npm run typecheck` e `npm run test:cov` continuam limpos, com cobertura ≥ 80% |
| RNF-D-006 | Nenhuma alteração em `backend/` |
| RNF-D-007 | Ícones como SVG inline com `currentColor`; emoji proibido |
| RNF-D-008 | Transições limitadas a 120–160 ms em cor, borda e fundo; respeitar `prefers-reduced-motion` |

## 14. Fases de implementação

| Fase | Conteúdo | Depende de |
|---|---|---|
| **1 — Fundação** | fontes auto-hospedadas, `styles/` com tokens, reset, tipografia e átomos; `index.html`; locale pt-BR | — |
| **2 — Átomos e moléculas** | átomos com comportamento (estado vazio, diálogo de confirmação, etapa de progresso); moléculas de status (hand-off, assinatura, análise), `ErrorMessageComponent` reescrito e movido | 1 |
| **3 — Organismos e páginas** | cabeçalho, login, documentos (tabela + trilho + formulário), painel de análise, organização, relatórios, alertas — com tradução | 2 |
| **4 — Comportamento novo** | filtros, paginação, confirmação de exclusão, estado "analisando", trilho em sobreposição | 3 |
| **5 — Acabamento** | passe de acessibilidade (seção 10), tema escuro conferido tela a tela, ajuste em 1280 px, atualização dos testes | 4 |

A Fase 4 é a única cortável sem prejudicar as demais. Cortada, as telas ficam completas
visualmente e o comportamento permanece o de hoje.

## 15. Impacto nos testes

Os 74 testes existentes são o contrato de comportamento e **não devem ser afrouxados**. O
que muda:

- Os 35 `data-testid` continuam existindo nos elementos equivalentes. É a razão de RF-D-024.
- Quatro asserções dependem de copy em inglês e precisam de atualização junto da tradução:
  - `alerts/alerts.component.spec.ts:66` — `'None.'`
  - `reports/reports.component.spec.ts:81` — `'No documents yet.'`
  - `shared/error-message.component.spec.ts:32,46` — `'Something went wrong.'`, `'Enter a valid URL.'`
  - (`core/auth/login.component.spec.ts:57` afirma `'No active account'`, que é `detail`
    vindo do backend — **não** é copy da interface e não muda.)
  - O spec de `error-message` acompanha o componente na mudança para `ui/molecules/`
    (RF-D-027); o conteúdo das asserções muda só pela tradução.
- Testes novos exigidos: renderização das três variantes de pastilha, do marcador de
  assinatura para valor desconhecido, dos quatro estados do painel de análise, e do
  diálogo de confirmação (confirma e cancela).

## 16. Critérios de aceite

```gherkin
Cenário: os dois status não se confundem
  Dado um documento com provider_status "submitted" e status de assinatura "pending"
  Quando eu olho a linha dele na lista
  Então o hand-off aparece como pastilha verde com ícone de check
  E a assinatura aparece como ponto vazado com o texto em versalete
  E as duas formas são visualmente distintas sem depender de cor

Cenário: falha de envio é recuperável, não fatal
  Dado um documento com provider_status "failed" e last_provider_error preenchido
  Quando eu olho a linha dele
  Então vejo a pastilha vermelha, o motivo do erro e a informação de que o documento está salvo
  E vejo o botão "Reenviar" na própria linha

Cenário: risco não é erro
  Dado um documento cuja análise mais recente tem um insight com risk verdadeiro
  Quando eu abro o painel de análise
  Então o insight aparece em ocre, com ícone de triângulo e o rótulo "RISCO"
  E nenhum elemento vermelho de falha aparece por causa dele

Cenário: falha de análise preserva o documento
  Dado uma análise com state "failed" e error_reason "no_text"
  Quando eu abro o painel
  Então vejo "no_text" em mono e a explicação em português
  E vejo que o documento e o envio não foram afetados
  E o botão de repetir é a ação primária do painel

Cenário: exclusão de organização com documentos
  Dado uma organização com 6 documentos
  Quando eu tento excluí-la
  Então vejo um banner com a causa, o código "company_has_documents" e o que fazer
  E a organização continua na lista

Cenário: tema escuro
  Dado que meu sistema está em tema escuro
  Quando eu abro qualquer tela
  Então todas as cores vêm dos tokens escuros
  E nenhum texto fica abaixo de 4.5:1 de contraste

Cenário: nada precisa de atenção
  Dado que não há documentos parados nem análises com risco
  Quando eu abro Alertas
  Então vejo uma confirmação afirmativa, com ícone de check
  E não vejo uma tela de erro nem uma área em branco
```

## 17. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Reescrever templates quebra testes silenciosamente | RF-D-024 preserva os `data-testid`; rodar `npm run test:cov` a cada tela concluída, não no fim |
| CSS duplicado estoura o orçamento de 4 kB por componente | Átomos globais (seção 12); medir com `npm run build` ao fim de cada fase |
| Tema escuro entregue sem conferência real | Fase 5 exige percorrer as sete telas nos dois temas antes do aceite |
| Fonte auto-hospedada infla o bundle | Só os pesos usados, subconjunto latin, `font-display: swap`; conferir contra o orçamento de 500 kB |
| Comportamento novo (Fase 4) atrasa o visual | A Fase 4 é isolada e cortável; a 3 entrega o design completo sem ela |
| Tradução deixa termo técnico inconsistente | Glossário da seção 11 é normativo; valores da API não se traduzem |

## 18. Definição de pronto

- [ ] As sete telas correspondem ao canvas nos dois temas.
- [ ] `npm run lint`, `npm run typecheck` e `npm run test:cov` limpos, cobertura ≥ 80%.
- [ ] `npm run build` dentro dos orçamentos de `angular.json`.
- [ ] Nenhum arquivo de `backend/` alterado.
- [ ] Nenhum import de camada baixa para camada alta (Princípio XI da constituição).
- [ ] Nenhuma requisição a domínio externo na aba de rede, com a aplicação offline.
- [ ] Navegação completa por teclado nas sete telas, com foco sempre visível.
- [ ] Contraste conferido nos dois temas.
- [ ] Interface inteira em pt-BR, com os valores técnicos preservados.
- [ ] README atualizado com a seção de sistema visual e a origem das fontes.
