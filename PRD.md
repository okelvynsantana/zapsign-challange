# PRD — Sistema de Gestão de Documentos e Assinaturas (com integração ZapSign)

**Produto:** Sistema próprio de gestão de documentos e signatários
**Módulo:** Gestão de Documentos, Signatários e Análise Inteligente de Conteúdo
**Versão:** 1.0 (Draft para desenvolvimento — projeto greenfield)
**Autor:** [seu nome]
**Data:** 01/09/2026
**Status:** Em desenvolvimento — construção do zero

---

## 0. Enquadramento do Projeto

Este PRD assume a perspectiva de **empresa cliente da ZapSign**, e não da ZapSign como produto. Ou seja: estamos construindo um **sistema próprio**, do zero, para gerenciar nossos contratos e signatários, e a ZapSign entra como **fornecedor externo de assinatura digital** — assim como o provedor de IA e o n8n são fornecedores/consumidores externos.

Implicações práticas dessa mudança de lente em relação à leitura literal do desafio original:
- `Company` deixa de ser uma entidade multi-tenant (várias empresas clientes da ZapSign). Ela passa a representar **a nossa própria empresa**, com seu `api_token` da ZapSign guardado para autenticar as chamadas.
- Autenticação do sistema é a **nossa própria** (usuários internos da nossa empresa acessando nosso painel), não autenticação de "clientes da ZapSign".
- Os endpoints RESTful expostos (para n8n, etc.) são **nossos**, não da ZapSign — nós que decidimos o contrato de API.
- Não há nenhum código, infraestrutura ou schema hoje. Tudo é decisão de arquitetura em aberto (ver seção 19).

## 1. Contexto e Problema

Hoje não existe, dentro da nossa operação, um lugar único para cadastrar e gerenciar documentos e signatários que precisam ser assinados digitalmente. O fluxo é manual e não oferece nenhum tipo de inteligência sobre o conteúdo enviado (ex: identificar cláusulas faltantes, resumir o documento, apontar riscos).

Isso gera três problemas para nós, como empresa:
1. **Lentidão operacional** — não há um lugar único para gerenciar documentos e signatários antes de mandar para assinatura via ZapSign.
2. **Falta de automação** — nossas próprias ferramentas de automação (n8n) não têm um jeito estruturado de disparar criação de documentos ou puxar relatórios.
3. **Falta de inteligência** — não recebemos nenhum insight automático sobre os documentos que enviamos para assinatura antes de eles saírem para os signatários.

## 2. Objetivo do Produto

Construir, do zero, um sistema de gestão de documentos que nos permita **cadastrar, listar, editar e excluir** documentos e signatários internamente, com **envio automático para a API da ZapSign** (nosso fornecedor de assinatura digital), **análise de conteúdo via IA** antes do envio, e **exposição de endpoints RESTful autenticados** próprios, para que nossas automações internas (n8n) consumam esses dados.

## 3. User Story Principal

> Como gerente da nossa empresa, quero poder cadastrar e gerenciar nossos documentos e signatários diretamente pelo nosso sistema, para acelerar a criação de contratos, assinar com mais agilidade (via ZapSign) e obter insights automáticos sobre os documentos antes de enviá-los.

## 4. Personas

| Persona | Descrição | Necessidade principal |
|---|---|---|
| Gerente interno | Usuário de negócio, não técnico, da nossa própria empresa | Criar/gerenciar documentos e signatários com rapidez, sem fricção |
| Time de automação (nós mesmos, via n8n) | Consome nossos endpoints para automatizar fluxos | Endpoints RESTful documentados, autenticados e estáveis |
| Time de desenvolvimento (nós) | Constrói e mantém o sistema do zero | Código testável, documentado, com arquitetura clara desde o dia 1 |

## 5. Escopo

### 5.1 Dentro do escopo (MVP)
- CRUD completo (Create, Read, Update, Delete) de **Company**, **Document** e **Signer**, via SPA (sem reload de página).
- Criação de documento dispara automaticamente a chamada à **API da ZapSign** (sandbox), persistindo `token` e `open_id` retornados.
- Análise de conteúdo do documento via **IA**, gerando: resumo, tópicos/cláusulas faltantes e insights úteis, exibidos ao usuário.
- Exposição de **endpoints RESTful autenticados** para: criação de documento, disparo de nova análise de IA e geração de relatórios — consumíveis por automações externas (n8n).
- **Testes automatizados** cobrindo as rotas e funcionalidades principais (backend: Pytest; frontend: Jest).
- **README** técnico explicando setup, execução de testes, consumo dos endpoints e lógica de IA aplicada.
- Ambiente reprodutível via **Docker**.

### 5.2 Fora do escopo (nesta fase)
- Fluxo de assinatura em si dentro do app (é feito pela ZapSign; o módulo apenas cria/gerencia o documento e consulta status).
- Gestão de usuários/permissões multi-nível (RBAC) — assume-se um usuário autenticado por empresa.
- Design visual polido (explicitamente não avaliado pelo desafio).
- Cobrança, planos, billing.

### 5.3 Bônus (desejável, não obrigatório)
- Painel com **alertas automáticos** (ex: documento parado há X dias, análise de IA identificou risco).
- Workflow **n8n demonstrativo** consumindo os endpoints da plataforma.
- Arquitetura em **Clean Architecture / DDD**.
- Desenvolvimento guiado por **TDD**.

## 6. Requisitos Funcionais

| ID | Requisito | Prioridade |
|---|---|---|
| RF01 | Usuário deve poder criar, listar, editar e excluir uma **Company** | Must |
| RF02 | Usuário deve poder criar, listar, editar e excluir um **Document**, associado a uma Company | Must |
| RF03 | Usuário deve poder criar, listar, editar e excluir um **Signer**, associado a um Document | Must |
| RF04 | Ao criar um Document, o sistema deve chamar a API da ZapSign (sandbox) e persistir `open_id`, `token` e `status` retornados | Must |
| RF05 | Formulário de criação de documento deve capturar: nome do documento, nome/e-mail do(s) signatário(s) e URL do PDF | Must |
| RF06 | Após salvar um Document, o sistema deve disparar análise de IA sobre o conteúdo, retornando resumo, tópicos faltantes e insights | Must |
| RF07 | Resultado da análise de IA deve ser exibido na interface, associado ao documento | Must |
| RF08 | Deve existir endpoint autenticado para criação de Document via API (uso por n8n/terceiros) | Must |
| RF09 | Deve existir endpoint autenticado para disparar **nova análise de IA** sobre um documento existente | Must |
| RF10 | Deve existir endpoint autenticado para geração de **relatório** (ex: resumo agregado de documentos/status/insights) | Must |
| RF11 | Exclusão de um Document deve excluir em cascata seus Signers associados | Must |
| RF12 | Interface deve atualizar a lista de documentos dinamicamente após criação/edição/exclusão, sem recarregar a página | Must |
| RF13 (bônus) | Painel deve exibir alertas automáticos baseados em regras (ex: documento pendente há N dias, insight de risco da IA) | Should |
| RF14 (bônus) | Deve haver um workflow n8n de exemplo integrado aos endpoints | Could |

## 7. Requisitos Não Funcionais

| ID | Requisito |
|---|---|
| RNF01 | API deve seguir padrão RESTful, com autenticação (ex: token/API key) em todos os endpoints expostos externamente |
| RNF02 | Cobertura de testes automatizados nas rotas e funcionalidades principais (backend e frontend) |
| RNF03 | Ambiente local deve subir via Docker (Docker Compose recomendado) com um comando |
| RNF04 | Chamadas à API da ZapSign e ao provedor de IA devem tratar falhas (timeout, erro de resposta) sem quebrar o CRUD local |
| RNF05 | README deve permitir que qualquer desenvolvedor suba o projeto, rode os testes e consuma os endpoints sem suporte adicional |
| RNF06 | Persistência em PostgreSQL, com schema criado via migrations |
| RNF07 | Frontend deve ser reativo (componentes Angular), sem reload de página nas operações de CRUD |
| RNF08 | Backend deve ser exposto via **Django REST Framework** (DRF) — serializers, viewsets/generics e autenticação DRF nativa como base da API |
| RNF09 | Código de backend deve seguir os princípios **SOLID**, com ênfase em inversão de dependência nas integrações externas (ZapSign, IA) via interfaces/gateways — evita acoplamento direto a SDKs/HTTP de terceiros na camada de domínio |
| RNF10 | Arquitetura de backend deve seguir princípios de **DDD** (Domain-Driven Design): camadas separadas de domínio, aplicação e infraestrutura; entidades e regras de negócio isoladas de Django/DRF onde fizer sentido, sem sobre-engenharia |
| RNF11 | Desenvolvimento guiado por **TDD** nos componentes críticos de regra de negócio (integração ZapSign, análise de IA, regras de status) — teste escrito antes da implementação |
| RNF12 | Decisões de design devem seguir **KISS** — preferir a solução mais simples que atenda o requisito; complexidade (assíncrono, cache, camadas extras) só é introduzida quando o requisito justificar, não por padrão |
| RNF13 | Backend deve ser organizado em **múltiplas apps Django** (separação de responsabilidades), ex: `companies`, `documents`, `signers`, `integrations` (ZapSign/IA), `automation` (n8n) — em vez de um único app monolítico |
| RNF14 | Todas as chaves primárias (PK) das entidades do domínio devem ser **UUID**, não inteiro auto-incremento — evita exposição de sequência/volume de dados via API e facilita futura distribuição/replicação |
| RNF15 | Toda a aplicação (backend, frontend, banco) deve ser **dockerizada**, com imagens preparadas para rodar tanto localmente (Docker Compose) quanto em **Kubernetes** (manifests/Helm chart, ou ao menos Dockerfiles compatíveis com deploy em k8s sem retrabalho) |
| RNF16 | API deve expor **endpoint de health check** (`/health/` ou `/api/health/`) verificando conectividade com banco e, idealmente, status das integrações externas — usado por probes de liveness/readiness do k8s |
| RNF17 | API deve ter **monitoração/observabilidade** básica: logs estruturados das chamadas às integrações externas (ZapSign, IA) e das rotas principais, com tempo de resposta e status — base mínima para acompanhar saúde da aplicação em produção |

## 8. Modelo de Dados

Baseado no diagrama de classes do desafio (PKs adaptadas para UUID, conforme RNF14 — os campos `open_id`/`token`/`external_id` continuam como retornados pela ZapSign, sem relação com nossa chave primária):

### Company
| Campo | Tipo | Observação |
|---|---|---|
| id | UUID (PK) | |
| name | string | |
| api_token | string | token **da nossa conta sandbox** na ZapSign |
| created_at | datetime | |
| last_updated_at | datetime | |

> Nota: mantemos `Company` como tabela (em vez de um valor fixo em config) porque o diagrama original assim define e isso deixa a porta aberta para, no futuro, o sistema suportar mais de uma empresa/CNPJ nossa com contas ZapSign distintas — mas no MVP, na prática, haverá uma única linha representando a nossa empresa.

### Document
| Campo | Tipo | Observação |
|---|---|---|
| id | UUID (PK) | |
| company_id | UUID (FK → Company) | |
| open_id | int | retornado pela API ZapSign (identificador deles, não nosso) |
| token | string | retornado pela API ZapSign |
| external_id | string | |
| name | string | |
| status | string | |
| created_by | string | |
| created_at | datetime | |
| last_updated_at | datetime | |

### Signer
| Campo | Tipo | Observação |
|---|---|---|
| id | UUID (PK) | |
| document_id | UUID (FK → Document) | |
| name | string | |
| email | string | |
| token | string | |
| status | string | |
| external_id | string | |

**Relações:** Company 1:N Document · Document 1:N Signer (exclusão em cascata de Document → Signer).

### DocumentAnalysis (decidido — não é mais "sugestão de evolução")
| Campo | Tipo | Observação |
|---|---|---|
| id | UUID (PK) | |
| document_id | UUID (FK → Document) | |
| summary | text | |
| missing_topics | json (array de string) | |
| insights | json (array de string) | |
| source | string | `"llm"`, `"regex"` ou `"llm+regex"` — ver seção 10.2 |
| created_at | datetime | |

Cada chamada a `POST /documents/{id}/analyze/` cria um novo registro (histórico auditável), em vez de sobrescrever a análise anterior. O endpoint de leitura do documento retorna a análise mais recente por padrão; histórico completo fica disponível via `GET /documents/{id}/analyses/`.

## 9. Fluxo Principal (resumo do diagrama de sequência)

1. Usuário insere dados do documento + signatário no frontend.
2. Frontend envia requisição de criação ao backend (Django).
3. Backend salva dados iniciais do documento localmente (antes da resposta da API).
4. Backend chama a API ZapSign (sandbox) com detalhes do signatário e URL do PDF.
5. ZapSign retorna `open_id`, `token`, `status`.
6. Backend atualiza o documento local com os dados retornados.
7. Backend dispara (síncrono ou assíncrono) a análise de IA sobre o conteúdo do documento.
8. Frontend recebe confirmação de sucesso e atualiza a lista de documentos sem reload de página.

## 10. Integrações

### 10.1 ZapSign API (sandbox)
- Base: `https://sandbox.api.zapsign.com.br/api/v1/docs/`
- Documentação: `https://docs.zapsign.com.br/`
- Autenticação: `api_token` armazenado por Company.
- Uso: criação de documento e consulta de status.

### 10.2 IA (análise de conteúdo) — decisão fechada

**Provedor:** OpenAI (chamada direta à API, sem LangChain). Justificativa: LangChain é uma camada de orquestração que não agrega valor para uma única chamada de prompt estruturado; adicionaria dependência e superfície de bugs sem ganho real neste escopo. spaCy e HuggingFace foram considerados e descartados como motor principal — spaCy é NLP tradicional (bom para NER, não para julgamento de conteúdo como resumo/insights); HuggingFace (local ou via Inference API) teria custo de infra/latência extra (peso do modelo local, ou cold start/rate limit na Inference API gratuita) sem ganho de qualidade sobre a OpenAI para este escopo, especialmente considerando que os documentos tendem a estar em português.

**Modo de execução:** síncrono (a chamada de IA acontece dentro do request de criação do documento, com timeout curto configurável, ex: 15s). Trade-off assumido conscientemente: mais simples de implementar/testar, mas acopla a latência da IA à resposta do `POST /documents/`. Documentar no README que, em produção/escala, a evolução natural é mover para processamento assíncrono (fila + worker), e que a interface abaixo já foi desenhada para isso.

**Isolamento:** toda a lógica de IA fica atrás de uma interface `AnalysisProvider` (ex: `analyze(document_text: str) -> AnalysisResult`), implementada por `OpenAIAnalysisProvider`. Isso permite:
- Trocar de provedor sem tocar na regra de negócio (inclusive migrar para HuggingFace ou outro provedor depois, se necessário).
- Mockar o provider nos testes Pytest (não bater na API real da OpenAI durante CI).
- Migrar de síncrono para assíncrono no futuro trocando apenas quem chama a interface, não a interface em si.

**Pipeline de análise:**
1. Extrair texto do PDF a partir da URL fornecida (`pypdf` ou `pdfplumber`).
2. Enviar o texto para o LLM com prompt estruturado, pedindo saída em JSON com os campos `summary`, `missing_topics`, `insights`.
3. Reforçar `missing_topics` com uma checagem complementar por regex/palavras-chave de cláusulas comuns em contrato (ex: rescisão, foro, vigência, confidencialidade) — reduz dependência de o LLM "lembrar" de checar tudo e serve como camada de validação (`source: "llm+regex"` no registro salvo).
4. Persistir o resultado em `DocumentAnalysis` (ver seção 8).

**Falha/indisponibilidade da IA:** se a chamada falhar ou estourar o timeout, o documento ainda é criado/salvo normalmente (a integração ZapSign não deve depender da IA), e o campo de análise fica marcado como `failed`, permitindo nova tentativa via `POST /documents/{id}/analyze/`.

### 10.3 n8n / Automações — decisão fechada (inbound + outbound)

**Inbound (obrigatório pelo desafio):** n8n consome nossos endpoints RESTful via node HTTP Request, autenticado por API Key (ver seção 10.4). Endpoints relevantes: criação de documento, nova análise, relatórios.

**Outbound (cobre os itens de bônus "alertas automáticos" e "workflow n8n demonstrativo" com pouco esforço extra):** quando um documento muda de status ou a análise de IA identifica um insight relevante, o backend dispara um `POST` para um Webhook do n8n (URL configurável via `N8N_WEBHOOK_URL` no `.env`). O workflow de exemplo entregue no repositório (JSON exportado do n8n) implementa:

`Webhook (recebe evento do nosso sistema)` → `IF (há insight de risco?)` → `HTTP Request (GET /documents/{id}/report/ no nosso sistema, buscando detalhes)` → `Notificação (Slack/Email)`.

Isso é entregue como arquivo `.json` exportável + captura de tela funcionando, sem depender de manter uma instância n8n ativa continuamente.

### 10.4 Autenticação — decisão fechada
- **Usuários internos (gerente, via frontend Angular):** autenticação por sessão/token simples do próprio Django (ex: `djangorestframework-simplejwt` ou token auth padrão do DRF).
- **Integrações externas (n8n → nossos endpoints):** API Key própria por integração (header `Authorization: Api-Key <key>`), gerada e revogável, sem envolver o `api_token` da ZapSign (que é exclusivamente para nós → ZapSign, nunca exposto a terceiros).
- Justificativa: JWT teria fricção maior de configurar num node HTTP Request do n8n para um cenário single-tenant; API Key é o padrão mais simples e defensável para esse caso de uso, e ainda é revogável/rotacionável.

## 11. Especificação de API (proposta)

| Método | Endpoint | Descrição | Auth |
|---|---|---|---|
| GET/POST | `/api/companies/` | Listar / criar empresas | Sim |
| GET/PUT/DELETE | `/api/companies/{id}/` | Detalhar / editar / excluir empresa | Sim |
| GET/POST | `/api/documents/` | Listar / criar documentos (dispara integração ZapSign) | Sim |
| GET/PUT/DELETE | `/api/documents/{id}/` | Detalhar / editar / excluir documento | Sim |
| POST | `/api/documents/{id}/analyze/` | Disparar nova análise de IA sobre o documento | Sim |
| GET | `/api/documents/{id}/analyses/` | Histórico de análises de IA do documento | Sim |
| GET | `/api/documents/{id}/report/` | Relatório do documento (status + última análise) | Sim |
| GET | `/api/reports/summary/` | Relatório agregado (todos os documentos) | Sim |
| GET/POST | `/api/signers/` | Listar / criar signatários | Sim |
| GET/PUT/DELETE | `/api/signers/{id}/` | Detalhar / editar / excluir signatário | Sim |
| GET | `/api/health/` | Health check — status do banco e, quando aplicável, das integrações externas. Usado por probes de liveness/readiness do k8s | Não |

**Auth:** endpoints de uso interno (frontend) usam token de sessão do usuário; endpoints de uso por integrações externas (n8n) usam API Key própria (header `Authorization: Api-Key <key>`) — ver seção 10.4. `/api/health/` é público (probes de infraestrutura não devem depender de credencial de aplicação).

**Webhook outbound (não é um endpoint nosso, é uma chamada que fazemos):** `POST {N8N_WEBHOOK_URL}` disparado em eventos de mudança de status de documento ou análise de IA concluída com insight relevante. Payload proposto: `{"event": "document.analyzed", "document_id": ..., "status": ..., "has_risk_insight": bool, "report_url": "/api/documents/{id}/report/"}`.

## 12. Stack Técnica (definida pelo desafio + decisões complementares)

- **Backend:** Django + Django REST Framework (DRF), PostgreSQL, PKs em UUID
- **Frontend:** Angular, componentes reativos
- **Integrações:** ZapSign API (sandbox), OpenAI (análise de conteúdo, síncrona, isolada via interface `AnalysisProvider`), n8n (inbound via API Key + outbound via webhook)
- **Extração de PDF:** `pypdf` ou `pdfplumber`
- **Testes:** Pytest (backend, com mocks para ZapSign/OpenAI, TDD nos componentes de integração), Jest (frontend)
- **Arquitetura:** SOLID (inversão de dependência nas integrações), DDD leve (apps separadas por domínio), KISS (sem complexidade não justificada por requisito)
- **Organização Django:** múltiplas apps (`companies`, `documents`, `signers`, `integrations`, `automation`, `core`) em vez de app único
- **Infra:** Docker (multi-stage, pronto para k8s) / Docker Compose para setup local / manifests Kubernetes (Deployment, Service, ConfigMap/Secret, probes de liveness/readiness)
- **Observabilidade:** endpoint de health check + logging estruturado das chamadas de integração e das rotas principais (tempo de resposta, status)

## 13. Critérios de Aceite (Gherkin, conforme desafio original)

- **Dado que** o usuário acessa o painel da empresa, **então** deve ser possível criar, listar, editar e excluir Companies, Documents e Signers, com interface fluida (sem reload).
- **Dado que** o usuário cria um novo documento, **então** ele deve ser enviado automaticamente para a API da ZapSign, armazenando o `token` e `open_id` retornados.
- **Dado que** o documento é salvo, **então** o sistema deve analisar seu conteúdo com IA e apresentar uma visão com tópicos faltantes, resumo e insights úteis.
- **Dado que** o cliente deseja integrar seus fluxos com ZapSign, **então** a plataforma deve expor endpoints RESTful autenticados para criação de documentos, nova análise e relatórios.
- **Dado que** o produto está sendo monitorado, **então** deve haver testes automatizados garantindo a estabilidade das principais rotas e funcionalidades.
- **Dado que** o cliente técnico acessa o projeto, **então** o README deve explicar como subir o sistema, rodar testes, consumir os endpoints e entender a lógica de IA aplicada.

## 14. Métricas de Sucesso (propostas)

| Métrica | Meta sugerida |
|---|---|
| Tempo médio de criação de um documento (formulário → confirmação) | < 5s (excluindo latência da IA) |
| Taxa de sucesso na integração com ZapSign | > 99% das chamadas sem erro não tratado |
| Cobertura de testes automatizados | > 80% nas rotas principais |
| Tempo de setup local (clone → app rodando) | < 10 min via Docker |

## 15. Riscos e Mitigações

| Risco | Mitigação |
|---|---|
| Latência/instabilidade do provedor de IA impacta UX | Timeout curto (15s) + estado `failed`/retry manual; evolução natural em produção seria processamento assíncrono (fila/task) |
| Qualidade da saída do modelo abaixo do esperado | Reforço por regex de cláusulas comuns (camada de validação independente do modelo) + interface `AnalysisProvider` permite trocar de modelo/provedor sem reescrever a regra de negócio |
| Falha na API ZapSign impede criação do documento | Salvar documento localmente antes da chamada, com status `pending_integration`, e permitir retry |
| Custo/limite de chamadas à IA em escala | Cachear análises por documento; permitir "nova análise" apenas sob demanda (RF09), não automática a cada edição |
| Endpoints expostos sem autenticação adequada | Estratégia de auth já definida (sessão para frontend, API Key para integrações) e coberta por testes |

## 16. Pré-condições Técnicas

- Conta criada no sandbox ZapSign: `https://sandbox.app.zapsign.com.br/`
- `api_token` da ZapSign coletado e persistido em `Company.api_token`
- Banco PostgreSQL criado com tabelas `Company`, `Documents`, `Signers` via migrations

## 17. Entregáveis

1. Backend (Django + DRF, apps separadas por domínio, PKs em UUID) com CRUD, integração ZapSign, análise de IA e endpoints autenticados.
2. Frontend (Angular) com CRUD reativo (sem reload) e formulário de criação de documento.
3. Testes automatizados (Pytest, com TDD nos componentes de integração; Jest no frontend).
4. `docker-compose.yml` para setup local + Dockerfiles multi-stage prontos para k8s.
5. Manifests Kubernetes (Deployment, Service, ConfigMap/Secret, probes de liveness/readiness em `/api/health/`).
6. Endpoint de health check + logging estruturado das integrações e rotas principais.
7. README com: instruções de setup, execução de testes, documentação dos endpoints, explicação da lógica de IA aplicada, e decisões de arquitetura (SOLID/DDD/KISS/UUID) justificadas.
8. (Bônus) Workflow n8n demonstrativo, painel de alertas.

## 18. Ponto de Partida — Projeto Greenfield

Não existe nenhum código, repositório, banco ou infraestrutura hoje. Antes de atacar os requisitos funcionais, há decisões de bootstrap a fechar:

### 18.1 Decisões de arquitetura a tomar antes de codar
- Monorepo (backend + frontend juntos) vs. dois repositórios separados.
- Estratégia de autenticação do sistema (não confundir com o `api_token` da ZapSign): sessão Django, JWT (ex: `djangorestframework-simplejwt`), ou API Key simples — dado que é uso interno/single-tenant no MVP, uma API Key própria por integração (n8n) + login simples para o gerente pode ser suficiente.
- Onde a chamada à IA acontece: síncrona (bloqueia a resposta do POST) ou assíncrona (fila/worker, ex: Celery + Redis) — decisão fechada em síncrona (ver seção 10.2), por KISS: assíncrono só se justifica quando o requisito pedir escala, não por padrão.
- Estrutura de apps Django (RNF13): separar desde o início em múltiplas apps — sugestão:
  - `companies/` — modelo e regras de `Company`
  - `documents/` — modelo, regras de `Document` e `DocumentAnalysis`
  - `signers/` — modelo e regras de `Signer`
  - `integrations/` — camada de infraestrutura: `ZapSignClient`, `AnalysisProvider` (implementação OpenAI) — isolada das apps de domínio (RNF09/RNF10)
  - `automation/` — endpoints e lógica específica de consumo por n8n (auth por API Key, disparo de webhook outbound)
  - `core/` (ou `common/`) — utilidades compartilhadas, health check, configuração de logging
- Dentro de cada app de domínio (`documents`, `signers`, `companies`), separar camadas leves de DDD: `models.py` (persistência), `services.py` ou `domain.py` (regras de negócio puras, sem depender de DRF), `serializers.py`/`views.py` (camada de API) — sem sobre-engenharia (KISS): não criar camada extra onde o modelo Django já resolve.

### 18.2 Ordem sugerida de construção (sprint única do desafio)
1. Scaffolding: apps Django separadas, Docker Compose (Postgres + Django + Angular), Dockerfiles multi-stage prontos para reuso em k8s, settings básicos, `.env.example`.
2. Migrations das tabelas (`Company`, `Document`, `Signer`, `DocumentAnalysis`) com PK em UUID + admin básico do Django para inspeção manual.
3. TDD nos componentes centrais: escrever testes de `ZapSignClient` e `AnalysisProvider` (com mocks) antes da implementação; CRUD de `Company`/`Document`/`Signer` via DRF + testes Pytest.
4. Integração com API sandbox da ZapSign no `create` de `Document` (camada `integrations/`, isolada e mockável).
5. Integração com OpenAI (camada `integrations/`, isolada via `AnalysisProvider`) + endpoint de nova análise.
6. Endpoint de health check (`/api/health/`) + logging estruturado das integrações externas (RNF16/RNF17).
7. Frontend Angular: listagem + formulário reativos, consumindo a API já pronta.
8. Endpoints "externos" (n8n) no app `automation/`: reaproveitam a mesma API de `documents`, com autenticação por API Key e documentação explícita no README.
9. Testes end-to-end das rotas principais + README final.
10. Manifests de Kubernetes (Deployment, Service, ConfigMap/Secret para variáveis sensíveis, probes de liveness/readiness apontando para `/api/health/`) — ou ao menos Dockerfiles/documentação deixando claro o caminho de deploy em k8s, dado o tempo do desafio.
11. (Se sobrar tempo) itens de bônus: alertas, workflow n8n de exemplo.

### 18.3 Riscos específicos de começar do zero
- Risco de gastar tempo demais no scaffolding (apps separadas, DDD, k8s) e pouco nos requisitos que valem pontos (integração ZapSign, IA, testes). Mitigação: aplicar KISS de fato — separação em apps e camadas leves de domínio, sem exagerar em abstração; manifests de k8s podem ficar simples/mínimos se o tempo apertar, documentando isso no README como escolha consciente.
- Risco de acoplar a lógica de negócio diretamente ao SDK/HTTP da ZapSign ou da OpenAI, dificultando testes e violando SOLID (inversão de dependência). Mitigação: interfaces/gateways (`ZapSignClient`, `AnalysisProvider`) desde a primeira versão, com mocks nos testes Pytest — isso também é o que viabiliza o TDD nesses componentes.
- Risco de UUID como PK gerar overhead de índice/legibilidade em debugging manual. Mitigação: usar `uuid4` via `models.UUIDField(default=uuid.uuid4, primary_key=True)` no Django, que é suporte nativo — não exige biblioteca extra nem lógica customizada.

## 19. Diagramas de Referência

O documento original do desafio inclui, como anexo:
- **Diagrama de Fluxo** (sequência: Usuário → Frontend Angular → Backend Django → PostgreSQL → ZapSign API sandbox)
- **Diagrama de Classes** (Empresa 1:N Documento 1:N Signatário)

Ambos devem ser usados como referência de arquitetura, mas podem ser refinados durante o desenvolvimento (ex: inclusão de `DocumentAnalysis` sugerida na seção 8).

---

**Contato para dúvidas sobre o desafio original:** rh@zapsign.com.br
