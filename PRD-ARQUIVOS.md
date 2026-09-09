# PRD — Upload, Armazenamento (Cloudflare R2), Visualização e Posicionamento de Assinatura

**Produto:** Sistema de Gestão de Documentos e Assinaturas (com integração ZapSign)
**Módulo:** Ciclo de vida do arquivo — upload, custódia, visualização, download e posicionamento
**Versão:** 2.0 (evolução do `PRD.md` v1.0)
**Feature sugerida:** `004-document-file-storage`
**Autor:** Kelvyn Santana
**Data:** 09/09/2026
**Status:** Draft para desenvolvimento
**Depende de:** `PRD.md` (v1.0, entregue), `PRD-DESIGN.md` (design system da SPA)

---

## 0. Enquadramento

Continuamos na perspectiva de **empresa cliente da ZapSign**: o sistema é nosso, a ZapSign é o
fornecedor de assinatura digital. O que muda nesta versão é **quem tem a custódia do arquivo**.

Hoje o `Document` guarda apenas um `pdf_url` — um link externo, apontado por quem cadastra
([backend/apps/documents/models.py](backend/apps/documents/models.py)). Nós nunca fomos donos do
byte. A partir desta versão, **nós passamos a ser o sistema de custódia do PDF**: o usuário faz
upload, nós guardamos no **Cloudflare R2**, e todo consumo posterior (visualização, análise de IA,
envio à ZapSign, download do assinado) parte do nosso armazenamento, não de um link de terceiro.

---

## 1. Contexto e Problema

### 1.1 O link externo não nos dá controle sobre o documento
O cadastro exige uma URL pública de PDF. Consequências que já sentimos:
- **Não há visualização no produto.** A UI só consegue exibir o link cru
  ([document-detail-rail.component.html:49](frontend/src/app/documents/document-detail-rail.component.html#L49));
  o usuário precisa sair do sistema para ver o que está prestes a mandar para assinatura.
- **O arquivo pode sumir, mudar ou nunca ter sido acessível.** O extrator de PDF já convive com
  isso — trata `unreachable`, `not_pdf`, `too_large`, `timeout`
  ([pdf/extractor.py](backend/apps/integrations/pdf/extractor.py)) — mas a análise de IA falha por
  um motivo que **não é do usuário nem nosso**: é do host do link.
- **Exige que o PDF esteja publicamente acessível na internet** para a ZapSign conseguir baixá-lo.
  Isso empurra contratos internos para hospedagens improvisadas (Drive público, WeTransfer, S3
  aberto). É um problema de segurança que nós criamos ao pedir uma URL.

### 1.2 Não existe download do documento assinado
O `signed_file` da ZapSign **é um link temporário de 60 minutos**
([docs da ZapSign](https://docs.zapsign.com.br/documentos/criar-documento)). Nós não o persistimos
em lugar nenhum. Na prática: **o artefato de maior valor do fluxo inteiro — o contrato assinado —
não é recuperável pelo nosso sistema**. Depois de uma hora, quem quiser o PDF assinado precisa
entrar no painel da ZapSign. O sistema que existe para "gerenciar documentos" não entrega o
documento.

### 1.3 A assinatura não é posicionada
Hoje enviamos `name`, `url_pdf` e `signers`
([zapsign/client.py](backend/apps/integrations/zapsign/client.py)) e nada mais. A assinatura cai
onde a ZapSign decidir, não na linha de assinatura do contrato. Para contratos com campo de
assinatura desenhado, isso gera retrabalho manual e documentos visualmente errados.

**Resumo:** somos um gerenciador de documentos que não guarda, não mostra, não devolve e não
posiciona o documento.

---

## 2. Objetivo do Produto

Assumir a custódia do arquivo de ponta a ponta: **o usuário sobe o PDF** (deixa de informar link),
**nós armazenamos no Cloudflare R2**, **exibimos o documento dentro do produto**, **posicionamos as
assinaturas visualmente antes do envio** e **guardamos o documento assinado de forma permanente,
com download disponível a qualquer momento**.

---

## 3. User Stories

> **US-A (P1) — Subir em vez de linkar.** Como gerente, quero enviar o arquivo PDF direto do meu
> computador ao cadastrar um documento, para não precisar hospedar o contrato em um link público.

> **US-B (P1) — Ver antes de mandar.** Como gerente, quero visualizar o PDF dentro do sistema,
> para conferir o conteúdo antes de disparar a assinatura.

> **US-C (P1) — Baixar o assinado.** Como gerente, quero baixar o documento assinado a partir do
> nosso sistema, a qualquer momento, para arquivar e comprovar o contrato.

> **US-D (P2) — Posicionar a assinatura.** Como gerente, quero marcar na página onde cada
> signatário assina, para que a assinatura saia na linha correta do contrato.

---

## 4. Personas

Mesmas do `PRD.md` §4. Nesta fase o **Gerente interno** é o usuário direto de todas as US, e o
**time de automação (n8n)** ganha um caminho de upload por API (RF24) e de download do assinado
(RF23) — hoje inexistentes.

---

## 5. Escopo

### 5.1 Dentro do escopo (MVP)
- Upload de PDF no formulário de documento (SPA), substituindo o campo de URL como caminho padrão.
- Armazenamento em **bucket privado no Cloudflare R2**, via interface de storage própria.
- **Visualizador de PDF embutido** na SPA (navegação por páginas, zoom), servido por URL assinada.
- **Download do original** e **download do assinado**, ambos a partir do nosso armazenamento.
- **Ingestão automática do `signed_file`** da ZapSign para o R2 assim que o documento é concluído
  — antes que o link de 60 minutos expire.
- **Posicionamento de assinatura por coordenadas**, com marcação visual sobre o preview do PDF, e
  sincronização com a ZapSign.
- Análise de IA passa a ler o PDF **do nosso storage**, não de uma URL externa.
- Migração dos documentos existentes (`pdf_url` legado continua funcionando; ver §17).
- Testes automatizados (Pytest/Jest) e atualização do README e do OpenAPI.

### 5.2 Fora do escopo (nesta fase)
- OCR de PDFs escaneados (segue falhando com `no_text`, como hoje).
- Edição/anotação do PDF dentro do produto.
- Múltiplos arquivos ou anexos por documento (a ZapSign suporta; nós não, ainda).
- Versionamento navegável de arquivos pelo usuário (o modelo suporta histórico; a UI mostra o atual).
- Assinatura acontecendo dentro do nosso app — continua na ZapSign.
- Posicionamento por **texto âncora** (`signature_placement` / `rubrica_placement`) — ver §5.3.

### 5.3 Bônus (desejável, não obrigatório)
- Posicionamento por **texto âncora** (`<<signer1>>`), útil para modelos padronizados de contrato.
- Rubrica (`type: "visto"`) além da assinatura.
- Verificação antivírus do upload antes de persistir.
- Miniatura (thumbnail) da primeira página na listagem de documentos.

---

## 6. Requisitos Funcionais

Numeração continua a do `PRD.md` (que termina em RF14).

| ID | Requisito | Prioridade |
|---|---|---|
| RF15 | O formulário de documento deve aceitar **upload de arquivo PDF**, substituindo a URL como caminho padrão de criação | Must |
| RF16 | O upload deve ser validado antes de persistir: extensão, `content-type`, **magic bytes `%PDF`** e tamanho máximo de **10 MB** (limite imposto pela ZapSign) | Must |
| RF17 | O arquivo deve ser armazenado em **bucket privado no Cloudflare R2**, sem qualquer acesso público ou anônimo | Must |
| RF18 | O documento deve persistir os metadados do arquivo: chave no bucket, tamanho, `content-type`, hash SHA-256 e número de páginas | Must |
| RF19 | A SPA deve **exibir o PDF embutido** na tela de detalhe do documento, com navegação de páginas e zoom | Must |
| RF20 | O acesso ao arquivo deve se dar por **URL assinada de curta duração** (TTL configurável, padrão 15 min), emitida apenas para usuário autenticado com acesso ao documento | Must |
| RF21 | O envio à ZapSign deve usar o arquivo **do nosso storage**, e não uma URL informada pelo usuário | Must |
| RF22 | Quando a ZapSign reportar o documento como concluído/assinado, o sistema deve **baixar o `signed_file` e persisti-lo no R2** dentro da janela de validade do link (60 min) | Must |
| RF23 | Deve existir **download do documento assinado** a partir do nosso armazenamento, disponível permanentemente, independente da ZapSign | Must |
| RF24 | Deve existir endpoint autenticado de upload para automações (n8n), aceitando o binário do PDF | Must |
| RF25 | A análise de IA deve extrair o texto **do arquivo armazenado**, eliminando as falhas `unreachable`/`timeout` de link externo | Must |
| RF26 | O usuário deve poder **marcar visualmente**, sobre o preview do PDF, a posição da assinatura de cada signatário (página, posição, tamanho) | Should |
| RF27 | As posições marcadas devem ser enviadas à ZapSign via `POST /docs/{doc_token}/place-signatures/`, após a criação do documento e antes do início da assinatura | Should |
| RF28 | O sistema deve validar as posições antes de enviar: página existente, valores 0–100 e **posição + tamanho ≤ 100** em cada eixo (regra da ZapSign) | Should |
| RF29 | Documentos legados com `pdf_url` devem continuar visualizáveis e consultáveis, marcados como origem "link externo" | Must |
| RF30 | Deve haver rotina de **backfill** que baixa os PDFs de documentos legados para o R2, com relatório de sucesso/falha por documento | Should |
| RF31 | Excluir um documento deve remover também seus objetos no R2 (original e assinado) | Must |
| RF32 | Toda falha de armazenamento (upload, leitura, assinatura de URL) deve ser tratada sem derrubar o CRUD local, com mensagem acionável ao usuário | Must |
| RF33 | O sistema deve registrar quem subiu o arquivo e quando (auditoria mínima) | Should |
| RF34 | A listagem de documentos deve indicar visualmente se há original e se há assinado disponível | Should |

---

## 7. Requisitos Não Funcionais

Numeração continua a do `PRD.md` (que termina em RNF17).

| ID | Requisito |
|---|---|
| RNF18 | O acesso ao R2 deve ficar atrás de uma **interface própria** (`FileStorage`), com implementações real (R2/S3), fake (testes) e local (MinIO). Domínio, serviços e views **nunca importam `boto3`** — Constituição, Princípio I, mesmo padrão de `ZapSignGateway` |
| RNF19 | Credenciais do R2 vivem em variáveis de ambiente / Secrets do k8s, nunca no repositório, e são **redigidas** de logs e mensagens de erro (mesmo tratamento do `api_token` da ZapSign) |
| RNF20 | O bucket é **privado por padrão**: sem ACL pública, sem domínio público, sem listagem anônima |
| RNF21 | URLs assinadas têm TTL curto (padrão 15 min, configurável) e são geradas **por requisição**, nunca persistidas em banco nem cacheadas em CDN |
| RNF22 | O upload deve ter limite de tamanho aplicado **durante o streaming**, não após carregar o corpo em memória (mesmo cuidado já adotado no extrator de PDF) |
| RNF23 | Chaves de objeto devem ser opacas e não adivinháveis: `documents/{company_id}/{document_id}/{kind}/{uuid}.pdf` |
| RNF24 | A ingestão do arquivo assinado deve ser **idempotente** e ter retry — perder a janela de 60 min não pode significar perder o documento (fallback: reconsultar a ZapSign e obter novo link) |
| RNF25 | Testes não podem depender de rede nem de bucket real: `FakeFileStorage` em memória cobre o caminho feliz e os de falha |
| RNF26 | O visualizador de PDF deve rodar no cliente (pdf.js), sem enviar o conteúdo do documento a terceiros |
| RNF27 | Novos endpoints documentados no OpenAPI (`drf-spectacular`) e refletidos na referência de chamadas usada pelo n8n |
| RNF28 | Custo previsível: R2 não cobra egress; ainda assim, definir política de ciclo de vida e monitorar volume armazenado |

---

## 8. Modelo de Dados

### 8.1 Alterações em `Document`
| Campo | Tipo | Observação |
|---|---|---|
| `source` | enum (`upload`, `external_url`) | Novo. `upload` é o padrão a partir desta versão |
| `pdf_url` | URL, **agora opcional** | Mantido para documentos legados (RF29) e para o modo `external_url` |

Propriedades de domínio novas: `original_file`, `signed_file` (o `DocumentFile` atual de cada tipo)
e `has_signed_file`.

### 8.2 Nova entidade `DocumentFile`
| Campo | Tipo | Observação |
|---|---|---|
| `id` | UUID (PK) | Conforme RNF14 |
| `document` | FK → Document (CASCADE) | |
| `kind` | enum (`original`, `signed`) | |
| `storage_key` | string | Chave no bucket (RNF23) |
| `bucket` | string | Permite migrar de bucket sem reescrever histórico |
| `content_type` | string | Sempre `application/pdf` no MVP |
| `size_bytes` | integer | |
| `sha256` | string | Deduplicação e prova de integridade |
| `page_count` | integer, nulo | Alimenta o visualizador e o posicionamento |
| `uploaded_by` | string | Auditoria (RF33) |
| `created_at` | datetime | |

Regra: **insert-only**, como `DocumentAnalysis`. O arquivo "atual" de cada tipo é o mais recente —
o histórico é a trilha de auditoria que a Constituição exige (Princípio VI).

### 8.3 Nova entidade `SignaturePlacement`
| Campo | Tipo | Observação |
|---|---|---|
| `id` | UUID (PK) | |
| `signer` | FK → Signer (CASCADE) | |
| `type` | enum (`signature`, `visto`) | Nomes da ZapSign; `signature` é o padrão |
| `page` | integer | **Base 0**, como a ZapSign espera |
| `relative_position_left` | decimal (0–100) | |
| `relative_position_bottom` | decimal (0–100) | |
| `relative_size_x` | decimal (0–100) | |
| `relative_size_y` | decimal (0–100) | |
| `synced_at` | datetime, nulo | Quando foi aceito pela ZapSign |

Invariante de domínio (RF28): `position + size ≤ 100` em cada eixo, e `page < page_count`.

---

## 9. Fluxo Principal

1. Gerente escolhe a organização, dá um nome ao documento, adiciona signatários e **anexa o PDF**.
2. Backend valida (RF16), calcula hash e páginas, grava no R2 e cria `Document` + `DocumentFile(original)`.
3. SPA exibe o PDF no visualizador (URL assinada, RF20) — o usuário confere o conteúdo.
4. (Opcional) O usuário arrasta o marcador de assinatura de cada signatário sobre a página.
5. Backend dispara a criação na ZapSign usando o arquivo do R2 (RF21) e persiste `open_id`, `token`,
   `status` e os `signer.token` retornados.
6. Havendo posicionamentos, o backend chama `place-signatures/` com os `signer_token` (RF27).
7. Análise de IA roda sobre o texto extraído do arquivo armazenado (RF25).
8. Ao ser notificado/observar a conclusão da assinatura, o backend baixa o `signed_file` **dentro
   da janela de 60 min** e cria `DocumentFile(signed)` (RF22).
9. Gerente visualiza e baixa o assinado pelo nosso sistema, indefinidamente (RF23).

---

## 10. Integrações

### 10.1 Cloudflare R2 — decisão fechada
- API **S3-compatible** via `boto3`, endpoint `https://{account_id}.r2.cloudflarestorage.com`.
- Bucket **privado**; acesso exclusivamente por URL assinada (`presigned GET`) de curta duração.
- Interface `FileStorage` (RNF18) com as operações: `put`, `get_stream`, `presigned_url`, `delete`, `exists`.
- **MinIO** no Docker Compose para desenvolvimento e testes de integração locais — mesma API S3,
  sem depender de conta Cloudflare para rodar o projeto.
- Variáveis novas: `R2_ACCOUNT_ID`, `R2_ENDPOINT_URL`, `R2_BUCKET`, `R2_ACCESS_KEY_ID`,
  `R2_SECRET_ACCESS_KEY`, `FILE_MAX_BYTES`, `FILE_PRESIGN_TTL_SECONDS`.

**Caminho do upload (decisão):** upload **via backend** (multipart), e não `presigned PUT` direto do
browser. Justificativa (KISS, RNF12): o limite é 10 MB, o volume é baixo, e passar pelo backend nos
permite validar magic bytes, calcular hash e contar páginas **antes** de gravar — validação que o
upload direto empurraria para depois. `presigned PUT` fica registrado como evolução caso o limite
de tamanho aumente.

### 10.2 ZapSign — o que muda
- **Envio do arquivo:** `url_pdf` passa a receber uma **URL assinada do R2** (TTL de 15 min), em vez
  de uma URL do usuário. Alternativa configurável: `base64_pdf`, para cenários onde nenhuma URL
  possa sair do nosso perímetro (custo: payload ~33% maior).
- **Posicionamento:** `POST /api/v1/docs/{doc_token}/place-signatures/`, com o array `rubricas`
  (`type`, `page` base 0, `relative_position_left`, `relative_position_bottom`, `relative_size_x`,
  `relative_size_y`, `signer_token`). Exige `signer_token` — portanto **depois** da criação do
  documento.
- **Arquivo assinado:** `signed_file` e `original_file` retornam **links válidos por 60 minutos**;
  daí a obrigação da ingestão imediata (RF22) e do retry (RNF24).
- O `ZapSignGateway` ganha `place_signatures(...)` e `fetch_signed_file(...)`; o `client.py` continua
  sendo o único módulo que conhece URLs e payloads da ZapSign.

### 10.3 Gatilho da ingestão do assinado
Duas fontes, complementares: **webhook de entrada da ZapSign** (evento de documento assinado) e o
**resync já existente** (`can_resync` / `get_document`), que passa a persistir o arquivo quando
detectar status concluído. O webhook dá latência baixa; o resync é a rede de segurança que garante
a idempotência de RNF24.

---

## 11. Especificação de API (proposta)

| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/documents/` | Passa a aceitar `multipart/form-data` com o campo `file`, além do JSON atual |
| POST | `/api/documents/{id}/file/` | Substitui/atualiza o PDF original de um documento existente |
| GET | `/api/documents/{id}/file/url/` | Devolve URL assinada do original (`{url, expires_at}`) — usada pelo visualizador |
| GET | `/api/documents/{id}/signed-file/url/` | Devolve URL assinada do assinado; 404 enquanto não existir |
| GET | `/api/documents/{id}/download/?kind=original\|signed` | Download direto (redirect 302 para a URL assinada) |
| PUT | `/api/documents/{id}/placements/` | Define as posições de assinatura (lista por signatário) |
| POST | `/api/documents/{id}/sync-signed-file/` | Força a ingestão do assinado (operacional/retry) |

Todas herdam a autenticação já existente (JWT para a SPA, API Key para automações) e são
documentadas via `drf-spectacular` (RNF27).

---

## 12. Decisões Técnicas

### 12.1 Fechadas
| Decisão | Escolha | Motivo |
|---|---|---|
| Provedor de storage | Cloudflare R2 (S3-compatible, `boto3`) | Sem custo de egress; API S3 permite fake local com MinIO |
| Visibilidade do bucket | Privado + URL assinada | O conteúdo é contratual; nada deve ser público (RNF20) |
| Caminho do upload | Via backend (multipart) | Valida antes de gravar; simples para o limite de 10 MB |
| Limite de arquivo | 10 MB | É o teto da ZapSign; adotar outro criaria erro só na hora do envio |
| Histórico de arquivo | Insert-only (`DocumentFile`) | Consistente com `DocumentAnalysis` e com a trilha de auditoria |
| Visualizador | pdf.js no cliente | O conteúdo não sai para terceiros; permite desenhar o overlay de posicionamento |
| Posicionamento | Coordenadas via `place-signatures/` | Funciona com qualquer PDF, sem exigir marcador no texto |

### 12.2 Em aberto (decidir na fase de plan)
- `url_pdf` assinado **ou** `base64_pdf` como padrão de envio à ZapSign (§10.2) — depende da postura
  de segurança que quisermos assumir para URLs assinadas saindo do perímetro.
- Biblioteca do visualizador: `pdfjs-dist` direto (mais controle sobre o overlay) vs.
  `ngx-extended-pdf-viewer` (mais pronto, menos controle).
- Ingestão do assinado síncrona no webhook vs. fila/worker (hoje o projeto não tem broker; introduzir
  um só se o requisito justificar — RNF12/KISS).
- Retenção: por quanto tempo guardamos originais de documentos excluídos (LGPD × necessidade probatória).

---

## 13. Critérios de Aceite (Gherkin)

```gherkin
Cenário: Upload substitui o link externo
  Dado que estou criando um documento
  Quando eu anexo um arquivo PDF de 4 MB e salvo
  Então o documento é criado sem que eu informe nenhuma URL
  E o arquivo fica armazenado no bucket privado

Cenário: Arquivo inválido é recusado
  Dado que estou criando um documento
  Quando eu anexo um arquivo que não é PDF ou que excede 10 MB
  Então recebo uma mensagem clara indicando o motivo
  E nada é gravado no bucket

Cenário: Visualização dentro do produto
  Dado um documento com arquivo armazenado
  Quando eu abro o detalhe do documento
  Então vejo o PDF renderizado na tela, com navegação de páginas
  E o acesso se deu por uma URL assinada de curta duração

Cenário: Download do documento assinado
  Dado um documento cuja assinatura foi concluída há mais de 60 minutos
  Quando eu clico em baixar o documento assinado
  Então recebo o PDF assinado a partir do nosso armazenamento
  E o download funciona mesmo que o link original da ZapSign já tenha expirado

Cenário: Posicionamento da assinatura
  Dado um documento com dois signatários e o PDF visível na tela
  Quando eu marco a posição da assinatura de cada um na página 2 e salvo
  Então as posições são enviadas à ZapSign junto do token de cada signatário
  E a assinatura aparece no local marcado no documento final

Cenário: Posição inválida é bloqueada
  Dado que estou posicionando uma assinatura
  Quando a soma da posição com o tamanho ultrapassa 100 em qualquer eixo
  Então o sistema recusa a marcação antes de chamar a ZapSign

Cenário: Documento legado continua funcionando
  Dado um documento antigo criado com link externo
  Quando eu o abro
  Então ele é exibido normalmente, identificado como origem "link externo"
```

---

## 14. Métricas de Sucesso

| Métrica | Alvo |
|---|---|
| Documentos criados por upload (vs. link externo) | ≥ 95% após 30 dias |
| Documentos assinados com PDF assinado persistido no R2 | 100% |
| Falhas de análise de IA por causa de link inacessível (`unreachable`/`timeout`) | Queda a ~0 |
| Tempo até o primeiro render do PDF no detalhe | < 2 s para arquivo de 5 MB |
| Documentos com assinatura posicionada (dos que usam posicionamento) | ≥ 90% saem na posição correta |
| Incidentes de exposição pública de arquivo | 0 |

---

## 15. Riscos e Mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| Perder a janela de 60 min do `signed_file` | Documento assinado irrecuperável pelo sistema | Ingestão disparada por webhook + resync idempotente com retry (RNF24); reconsulta gera link novo |
| URL assinada vazar enquanto válida | Acesso indevido ao contrato | TTL curto, chave opaca, URL nunca persistida nem cacheada (RNF21/RNF23) |
| Upload de arquivo malicioso | Segurança | Validação de magic bytes e tamanho; antivírus listado como bônus (§5.3) |
| ZapSign não conseguir baixar a URL assinada | Documento não sai para assinatura | Fallback configurável para `base64_pdf` (§10.2) |
| Custo/volume de storage crescer sem controle | Custo | Política de ciclo de vida + monitoração de volume (RNF28) |
| Acoplamento a `boto3` espalhado pelo código | Dívida arquitetural | Interface `FileStorage` obrigatória (RNF18), como já é feito com a ZapSign |
| Backfill dos legados falhar em massa | Inconsistência | Backfill idempotente, com relatório por documento; `pdf_url` continua válido enquanto não migrar (RF29) |

---

## 16. Segurança e Privacidade

- Bucket privado, sem domínio público e sem ACL anônima (RNF20).
- Credenciais R2 em Secret do k8s / `.env` não versionado, redigidas de logs (RNF19).
- URL assinada emitida **por requisição**, apenas para usuário autenticado com acesso ao documento.
- Chave de objeto opaca — conhecer o `document_id` não permite adivinhar o caminho do arquivo.
- Exclusão do documento remove os objetos (RF31); retenção de excluídos é decisão em aberto (§12.2).
- Nenhum conteúdo de contrato trafega para terceiros além de: ZapSign (necessário para assinar) e
  provedor de IA (já previsto no `PRD.md` §10.2).

---

## 17. Migração e Rollout

1. **Fase 1 — Aditiva.** Criar `FileStorage`, `DocumentFile`, endpoints e visualizador. `pdf_url`
   continua aceito. Nada quebra.
2. **Fase 2 — Upload como padrão.** SPA passa a oferecer upload como caminho principal; o campo de
   URL vira opção secundária ("usar link externo").
3. **Fase 3 — Backfill.** Comando de gestão baixa os PDFs dos documentos legados para o R2 (RF30),
   com relatório. Documentos cujo link morreu permanecem como `external_url` e são sinalizados.
4. **Fase 4 — Assinado retroativo.** Para documentos já concluídos, reconsultar a ZapSign e
   persistir o `signed_file` no R2.

`pdf_url` **não é removido** nesta versão. Vira campo opcional e legado.

---

## 18. Impacto no Código Existente

| Área | Mudança |
|---|---|
| [backend/apps/documents/models.py](backend/apps/documents/models.py) | `pdf_url` opcional, campo `source`, entidade `DocumentFile`, propriedades `original_file`/`signed_file` |
| [backend/apps/signers/models.py](backend/apps/signers/models.py) | Relação com `SignaturePlacement` |
| [backend/apps/integrations/zapsign/gateway.py](backend/apps/integrations/zapsign/gateway.py) | `place_signatures(...)`, `fetch_signed_file(...)`, `ZapSignCreateRequest` aceitando arquivo em vez de URL do usuário |
| [backend/apps/integrations/zapsign/client.py](backend/apps/integrations/zapsign/client.py) | Chamada a `place-signatures/`, payload com `url_pdf` assinado ou `base64_pdf` |
| [backend/apps/integrations/pdf/extractor.py](backend/apps/integrations/pdf/extractor.py) | Extrair de **bytes/stream** do storage, não só de URL; `page_count` exposto |
| `backend/apps/integrations/storage/` (novo) | `FileStorage`, `R2FileStorage`, `FakeFileStorage` |
| [backend/apps/documents/services.py](backend/apps/documents/services.py) | Orquestração de upload, ingestão do assinado e sincronização de posições |
| [backend/apps/automation/](backend/apps/automation/) | Webhook de entrada da ZapSign para disparar a ingestão |
| [frontend/src/app/core/models/document.model.ts](frontend/src/app/core/models/document.model.ts) | `pdf_url` opcional, `source`, `original_file`, `signed_file`, `placements` |
| [frontend/src/app/documents/document-form.component.html](frontend/src/app/documents/document-form.component.html) | Campo de upload substituindo o `input type="url"` |
| [frontend/src/app/documents/document-detail-rail.component.html](frontend/src/app/documents/document-detail-rail.component.html) | Visualizador embutido + botões de download no lugar do link cru |
| `frontend/src/app/documents/pdf-viewer` (novo) | Visualizador pdf.js + overlay de posicionamento |
| [deploy/](deploy/) | Serviço MinIO no Compose, variáveis R2 no `.env.example`, Secret no k8s |

---

## 19. Entregáveis

- Migrations do novo modelo, com `pdf_url` tornado opcional sem perda de dados.
- Interface `FileStorage` com implementação R2 e fake, coberta por testes (RNF25).
- Endpoints da §11 documentados no OpenAPI e na referência de chamadas do n8n.
- Visualizador de PDF e UI de posicionamento na SPA.
- Comando de backfill com relatório.
- README atualizado: como configurar R2, como rodar com MinIO local, limites de arquivo.
- Testes: upload válido/inválido, emissão de URL assinada, ingestão do assinado (incluindo link
  expirado), validação de posicionamento, e o caminho legado com `pdf_url`.

---

## 20. Próximo Passo

Rodar `/speckit-specify` a partir deste PRD para gerar `specs/004-document-file-storage/spec.md`,
seguido de `/speckit-plan` e `/speckit-tasks` — mesmo caminho usado na feature 001.

---

### Referências
- [Criar documento via Upload — ZapSign](https://docs.zapsign.com.br/documentos/criar-documento)
- [Opcional: Posicionar assinaturas — ZapSign](https://docs.zapsign.com.br/documentos/opcional-posicionar-assinaturas)
