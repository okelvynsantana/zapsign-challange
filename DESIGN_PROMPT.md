# Prompt de design — Document & Signature Management

> Cole o conteúdo abaixo (da linha "## Contexto" em diante) em uma conversa com o Claude,
> junto do comando `/design`, para gerar o canvas de telas.

---

## Contexto

Você vai desenhar a interface de um **sistema interno de gestão de documentos e assinaturas**.
Não é um produto público: quem usa é o time de operações/jurídico de uma empresa, várias vezes
por dia, em desktop. A prioridade é **densidade de informação, leitura rápida de status e
recuperação de erro** — não é uma landing page.

O que o sistema faz, em uma frase: cadastra o perfil da organização, cria documentos com seus
signatários, envia esses documentos para a **ZapSign** (provedor externo de assinatura
eletrônica) e roda uma **análise de conteúdo por IA** em cada PDF, produzindo resumo, tópicos
contratuais faltantes e insights — alguns marcados como risco.

Stack existente (o design precisa ser implementável nela): **Angular 19 standalone + SCSS puro**.
Não há Tailwind, Angular Material nem nenhuma biblioteca de componentes — tudo é CSS escrito à
mão. Então prefira um sistema visual baseado em tokens (custom properties CSS), tipografia de
sistema e componentes simples, sem depender de nada exótico.

### O conceito central que o design precisa comunicar

Existem **dois status diferentes** em cada documento, e confundi-los é o maior risco de UX:

1. **Hand-off (`provider_status`)** — o estado da *nossa* integração com a ZapSign:
   - `pending_integration` — gravado localmente, envio ainda em andamento
   - `submitted` — a ZapSign aceitou o documento
   - `failed` — a chamada falhou; há uma mensagem de erro e um botão **Resync** para tentar de novo
2. **Assinatura (`status`)** — string livre reportada pela ZapSign (ex.: `pending`, `signed`),
   nunca calculada por nós. Pode ser vazia/`—`.

O documento **sempre é criado localmente antes** de qualquer chamada externa: uma falha da
ZapSign ou da IA nunca perde o documento, só deixa um estado retentável. A interface deve deixar
isso óbvio — falha é um estado normal com ação de recuperação clara, não uma tela de erro fatal.

### Usuário

Um gestor interno autenticado (login por usuário/senha). Uma única persona; não há níveis de
permissão na UI.

---

## Telas a desenhar

Desenhe cada uma como um artboard separado, em desktop (1440px). Onde eu marcar, inclua também
uma variação de estado.

### 1. Login
Formulário mínimo centralizado: usuário, senha, botão "Entrar". Precisa de um estado de erro
inline ("credenciais inválidas") e um estado de carregamento no botão. É a única tela sem o
shell de navegação.

### 2. Documentos (tela principal — invista aqui)
É onde o usuário passa o tempo. Contém, hoje, três coisas empilhadas que provavelmente merecem
um layout melhor:

**a) Formulário de criação** — campos: Organização (select), Nome do documento, Link do PDF (URL),
Referência externa (opcional), e uma **lista dinâmica de signatários** (nome + e-mail, com
adicionar/remover linha; pelo menos um obrigatório, e-mails não podem repetir). Botão principal:
"Criar e enviar para assinatura". O mesmo formulário serve para edição, com "Salvar alterações"
+ "Cancelar".

**b) Lista de documentos** — tabela com: Nome (clicável, abre o detalhe), Hand-off (badge de
status + mensagem de erro quando houver), Assinatura, nº de signatários e ações (Resync — só
aparece em `submitted`/`failed` —, Editar, Excluir). Deve suportar filtros por hand-off, por
status de assinatura e por organização.

**c) Painel de detalhe do documento selecionado** — id ZapSign (`open_id`), token, URL do PDF,
lista de signatários com nome, e-mail e status individual, e abaixo o **painel de análise de IA**.

**Painel de análise de IA** (componente destacado, dentro do detalhe):
- Resumo em texto corrido
- **Tópicos faltantes** — lista de cláusulas comuns ausentes (ex.: "vigência", "foro", "multa")
- **Insights** — lista onde cada item pode carregar uma marca de **Risco** visualmente forte
- Rodapé com a procedência: "Produzido por `llm` / `regex` / `llm+regex`" e o modelo usado
- Ações: **Re-analisar** (com estado "Analisando…") e **Mostrar/ocultar histórico**
- **Histórico**: análises são append-only — cada re-execução vira uma nova entrada com data,
  resultado (`succeeded`/`failed`), procedência e quantidade de insights de risco
- Estados a desenhar: análise bem-sucedida, análise **falha** (mostra o motivo — `unreachable`,
  `not_pdf`, `too_large`, `no_text`, `timeout` — e deixa claro que o documento está intacto e a
  ação pode ser repetida) e "nenhuma análise ainda"

Variações pedidas desta tela: **lista vazia** ("nenhum documento ainda") e **lista com um
documento em `failed`** mostrando erro + Resync.

### 3. Organização
Perfil da empresa: Nome + **token da API ZapSign**. O token é write-only — na leitura só volta
mascarado (ex.: `zs_live_••••••4f2a`), e na edição o campo fica vazio com o texto "deixe em
branco para manter o token atual". Tabela com as organizações cadastradas e ações editar/excluir.
Excluir uma organização que ainda tem documentos é **recusado** — desenhe essa mensagem de erro.
O tratamento visual do campo de credencial deve transmitir "isto é segredo".

### 4. Relatórios
Visão agregada, hoje só listas de texto — merece virar um painel legível:
- Total de documentos
- Distribuição por status de hand-off
- Distribuição por status de assinatura
- Quantidade de documentos com insight de risco
- Insights de risco recentes (nome do documento + texto do insight)

Se usar gráficos, mantenha-os simples e legíveis; a contagem exata importa mais que a estética
do gráfico.

### 5. Alertas
Fila operacional do que precisa de atenção, em dois grupos:
- **Documentos parados** — pendentes há mais dias que o limite configurado (ex.: "pendente há 9 dias")
- **Achados de risco** — documentos cuja análise mais recente marcou um insight como risco

Cada alerta traz o nome do documento e o detalhe, e deve levar ao documento. Tem botão
"Atualizar". Desenhe também o **estado vazio** — "nada precisa de atenção agora" — que aqui é um
resultado bom, não uma ausência de dados.

### 6. Shell de navegação
Cabeçalho ou sidebar com o título do produto e os quatro destinos (Documentos, Organização,
Relatórios, Alertas) + sair. Indique o item ativo. Se Alertas tiver itens, considere um contador.

---

## Requisitos de design

- **Sistema visual primeiro**: defina tokens de cor, tipografia, espaçamento e raio antes das
  telas, e mostre-os em um artboard de "design system" com os componentes recorrentes (badge de
  status, botão primário/secundário/perigo, campo de formulário, linha de tabela, card de alerta,
  mensagem de erro, estado vazio).
- **Vocabulário de status consistente**: cada valor de hand-off (`pending_integration`,
  `submitted`, `failed`) e cada estado de análise (`succeeded`, `failed`) precisa de uma cor e
  forma fixas, usadas igual em todas as telas. Não dependa só de cor — inclua texto e/ou ícone.
- **Risco tem tratamento próprio**, distinto de "erro do sistema": um insight de risco é um achado
  sobre o contrato, não uma falha da aplicação.
- **Estados completos**: para cada tela, carregando, vazio e erro. Erros da API vêm como
  `{ detail, code, fields }` — erros de validação por campo devem aparecer junto do campo.
- **Densidade de desktop**, com um layout que não quebre em 1280px. Mobile não é prioridade.
- **Acessibilidade**: contraste AA, foco visível, tabelas com cabeçalho semântico, mensagens de
  erro associadas ao campo.
- **Tema claro e escuro** definidos por tokens.
- Textos da interface em **português do Brasil** (a versão atual está em inglês; considere isso
  parte do redesign) — mas mantenha os valores técnicos de status como aparecem na API.

## O que evitar

- Estética de landing page: gradientes decorativos, ilustrações grandes, hero sections.
- Esconder o motivo de uma falha atrás de um ícone ou tooltip — o erro da ZapSign e o motivo da
  análise falha são informação de primeira classe.
- Misturar visualmente os dois status (hand-off e assinatura).
- Componentes que exijam uma biblioteca de UI para implementar.

## Entregável

Um canvas com os artboards: design system, Login, Documentos (estado principal + vazio + falha),
Detalhe do documento com análise (sucesso + falha), Organização, Relatórios, Alertas (com itens +
vazio). Anote as decisões que não são óbvias pelo pixel — por que um status tem aquela cor, o que
acontece ao clicar em Resync.
