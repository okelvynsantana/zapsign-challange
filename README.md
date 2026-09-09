# Document & Signature Management System

An internal system for managing an organization profile, documents and signers, submitting
documents to **ZapSign** for signature, and running an **AI content analysis** over each
document (summary, missing clauses, insights). Authenticated REST endpoints let internal
automation create documents, re-run analysis and pull reports.

Angular SPA · Django + DRF API · PostgreSQL · Docker Compose · Kubernetes (Kustomize) · GitHub Actions

> ZapSign challenge. Built with spec-driven development: the specification, plan, data
> model and contracts in `specs/001-document-signature-management/` were written first and
> drove the implementation — see [Project documentation](#project-documentation).

---

## Quick start

```bash
cp deploy/.env.example deploy/.env      # every variable is documented inline
docker compose -f deploy/docker-compose.yml up --build
```

That brings up `db` (PostgreSQL 16), a one-shot `migrate` job (migrations + seed user),
`backend` on `:8000` and `frontend` on `:4200`.

```bash
curl -s localhost:8000/api/health/      # {"status":"ok","checks":{"database":"ok",...}}
open http://localhost:4200              # sign in with SEED_USERNAME / SEED_PASSWORD
```

### Running it offline

The analysis provider falls back to its in-process fake automatically when `OPENAI_API_KEY`
is blank, so the AI flow works with no key and no cost. **ZapSign does not fall back
implicitly** — a real token is a real token. To demo the whole flow with no network and no
sandbox account, set:

```bash
ZAPSIGN_USE_FAKE=true    # FakeZapSignGateway; AI_USE_FAKE=true forces the AI fake too
```

Without it, document creation calls the configured ZapSign environment and — with no valid
token — lands in `provider_status=failed` with the reason recorded, which is the retryable
state by design.

`specs/001-document-signature-management/quickstart.md` walks through validating every user
story with `curl`.

### Running without Docker

```bash
cd backend && python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python manage.py migrate && .venv/bin/python manage.py seed_user
.venv/bin/python manage.py runserver          # http://localhost:8000

cd frontend && npm ci && npm start            # http://localhost:4200
```

`POSTGRES_DB` selects PostgreSQL; with it unset the backend falls back to SQLite so a bare
clone runs with no database server. **Production and CI always run PostgreSQL.**

---

## Tests and quality gates

```bash
# backend — from backend/
ruff check . && ruff format --check .        # lint + format
mypy .                                        # full type check, no ignores outstanding
pytest --cov                                  # gate: >= 80% (currently 94%)

# frontend — from frontend/
npm run lint && npm run typecheck && npm run test:cov   # gate: >= 80% (currently 86%)
```

CI (`.github/workflows/`) runs all of it: `backend.yml` (ruff + mypy + pytest against a
`postgres:16` service, coverage gate), `frontend.yml` (eslint + tsc + jest + build) and
`images.yml` (image builds, pushed only from the default branch).

**The suite never reaches a third party.** ZapSign and OpenAI are mocked at the HTTP/SDK
boundary, and a session-wide fixture forces every gateway to its fake.

---

## Operator commands

```bash
python manage.py seed_user                 # the internal manager the SPA signs in as
python manage.py seed_demo                 # a demo company + document, idempotent
                                           # (uses the ZapSign fake; --real-provider opts in)
python manage.py create_api_key "n8n"      # prints the plaintext key ONCE
python manage.py revoke_api_key <prefix>   # subsequent calls with that key fail
```

---

## API

Full reference: [`contracts/rest-api.md`](specs/001-document-signature-management/contracts/rest-api.md)
and [`openapi.yaml`](specs/001-document-signature-management/contracts/openapi.yaml).
The running app serves a generated schema at `/api/schema/` and Swagger UI at `/api/docs/`.

### Authentication

| Scheme | Header | Used by | Applies to |
|---|---|---|---|
| JWT | `Authorization: Bearer <access>` | the SPA | all `/api/**` except health and auth |
| API key | `Authorization: Api-Key <key>` | external automation | `/api/automation/**`, plus the shared report reads |
| none | — | infra probes | `/api/health/` only |

A JWT is rejected on `/api/automation/**` and an API key cannot act as a SPA session.
Missing, malformed, expired or unknown credentials return `401`; a **revoked** key returns
`403`. Neither ever returns resource data.

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health/` | DB + integration status; unauthenticated, for k8s probes |
| `POST` | `/api/auth/token/`, `/api/auth/token/refresh/` | obtain / refresh the SPA JWT |
| `GET POST` | `/api/companies/` | organization profiles (the credential is write-only) |
| `GET PATCH DELETE` | `/api/companies/{id}/` | delete is refused with `409` while documents exist |
| `GET POST` | `/api/documents/` | list (filter by `provider_status`, `status`, `company`) / create |
| `GET PATCH DELETE` | `/api/documents/{id}/` | delete cascades to signers and analyses |
| `POST` | `/api/documents/{id}/resync/` | retry or refresh the ZapSign hand-off |
| `POST` | `/api/documents/{id}/analyze/` | run a **new** analysis |
| `GET` | `/api/documents/{id}/analyses/` | analysis history, newest first |
| `GET` | `/api/documents/{id}/report/` | status + latest analysis (JWT **or** API key) |
| `GET` | `/api/reports/summary/` | aggregated report (JWT **or** API key) |
| `GET` | `/api/alerts/` | stalled + risk alerts (bonus) |
| `GET POST` | `/api/signers/` | standalone signer management |
| `POST` | `/api/automation/documents/` | create a document (API key only) |
| `POST` | `/api/automation/documents/{id}/analyze/` | new analysis (API key only) |
| `GET` | `/api/automation/documents/{id}/report/` | per-document report (API key only) |
| `GET` | `/api/automation/reports/summary/` | aggregated report (API key only) |

---

## How document creation works

```
POST /api/documents/
  │
  ├─ 1. write Document (provider_status=pending_integration) + Signers   ← one transaction
  │                                                                        committed FIRST
  ├─ 2. ZapSign create_document
  │       ok    → provider_status=submitted, open_id/token/status stored,
  │               per-signer tokens matched back by email
  │       fail  → provider_status=failed, last_provider_error set        → retry via /resync/
  │
  ├─ 3. Analysis pipeline (extract PDF → LLM → regex clause pass)
  │       → a NEW DocumentAnalysis row, succeeded or failed              → retry via /analyze/
  │
  └─ 201, always — the local resource exists regardless of what step 2 or 3 did
```

Step 1 happening before step 2 is the whole resilience story: **no third-party outage can
cost us a document.** Step 3 cannot affect step 2, and neither can affect step 1.

## The AI analysis pipeline

1. **Extract** — fetch the PDF (bounded timeout, size cap enforced while streaming) and
   pull text with `pypdf`. Failure (`unreachable`, `not_pdf`, `too_large`, `no_text`,
   `timeout`) ends the run as a recorded `failed` analysis; the model is never called.
2. **Model** — one direct OpenAI call (`gpt-4o-mini` by default, no LangChain) asking for a
   strict JSON object: `summary`, `missing_topics`, `insights[{text, risk}]`, in pt-BR.
   Retries are disabled so the call stays inside its time budget.
3. **Regex reinforcement** — an independent keyword pass for common Brazilian contract
   clauses (objeto, vigência, rescisão, multa, foro, confidencialidade, pagamento, LGPD).
   Anything it finds that the model missed is merged in, and `source` becomes `llm+regex`.
4. **Graceful degradation** — if the model is unavailable, the regex pass alone still
   produces a useful `succeeded` result with `source="regex"` (switch off with
   `AI_REGEX_FALLBACK_ENABLED=false` to record a `failed` analysis instead).

Analyses are **append-only**: a re-run inserts a new row and the history is kept (FR-017).
`latest_analysis` is simply the newest by `created_at`.

---

## Architecture

```
backend/apps/
├── core/          UUID/timestamp model bases, SecretString, JSON logging, request timing,
│                  error handler, pagination, /api/health/
├── companies/     Company (the ZapSign credential lives here, masked on read)
├── documents/     Document + DocumentAnalysis, status rules, services, reports, alerts
├── signers/       Signer (unique email per document, cascade-deleted with its document)
├── integrations/  ZapSign · OpenAI · PDF · webhook — one ABC each, real + fake impls
└── automation/    API-key auth, the /api/automation/** surface, outbound webhook
```

**Design stance — idiomatic Django, decoupled where it pays.** Business rules live on the
models (`clean()`, methods, properties, `TextChoices`); reusable query logic lives in
`querysets.py`; `services.py` holds only the three use cases that span several models *and*
an external call (create / resync / analyze), as plain typed functions that receive their
gateways by injection. There is deliberately **no repository pattern and no dataclass
mirror of the ORM** — the ORM is the persistence abstraction and `QuerySet` is the query
abstraction, and restating them would be exactly the speculative layer the project's
simplicity principle forbids.

What *is* strictly decoupled is every third party. `ZapSignGateway`, `AnalysisProvider`,
`PdfTextExtractor` and `WebhookNotifier` are ABCs with a real and a fake implementation, and
nothing outside `integrations/` imports `httpx`, `openai` or `pypdf`. That is the seam that
makes failure paths testable and the providers swappable.

Full reasoning: [`plan.md` → Architecture Stance](specs/001-document-signature-management/plan.md).

### Data model

UUID v4 primary keys throughout (sequential ids leak volume through the API). `Signer` is
cascade-deleted with its `Document`; `Company` deletion is *refused* (`409`) while it still
has documents rather than orphaning them; `DocumentAnalysis` is insert-only.

---

## Visual system

The SPA is styled from a token layer rather than per-component values. Every colour, type step,
spacing step, radius and control height resolves from a CSS custom property declared in
`frontend/src/styles/_tokens.scss`; the full list is
[`contracts/design-tokens.md`](specs/003-spa-design-system/contracts/design-tokens.md).

**Two themes, no JavaScript.** Tokens have their base definition on `:root` and are *redefined*
under `@media (prefers-color-scheme: dark)` (guarded as `:root:not([data-theme="light"])`) and
again under `:root[data-theme="dark"]`. Nothing is stored and nothing is read at runtime, so there
is no flash on first paint and no state to test. A token whose only definition lives inside a theme
block is a defect — `frontend/src/styles/tokens.spec.ts` fails the build for it.

**Three status vocabularies that never converge.** This is the rule the interface is built around:

| Scale | Field | Form |
|---|---|---|
| Hand-off (ours) | `provider_status` | a bordered badge with an icon — the only scale drawn this way, because it is the only state we own and the only one with a retry |
| Signature (theirs) | `status` | a dot plus a small-caps label, never a badge; the value set is open, so an unrecognised value renders verbatim rather than breaking |
| Analysis | `latest_analysis` | icon plus text; a **risk** finding is ochre, a **failed** run is red, and they never share a colour or a mark |

No status is ever communicated by colour alone. API-recorded values (`submitted`, `no_text`,
`company_has_documents`) are displayed exactly as recorded, in the mono face — translating them
would create a second truth against the logs and the API docs.

**Composition.** Components follow Atomic Design with a one-way import rule: atoms know no domain
model, molecules bind one domain value, organisms may inject services, pages own routing and data.
Reusable pieces live in `frontend/src/app/ui/{atoms,molecules,organisms}/`; an organism used by one
screen stays in that screen's folder. Behaviourless atoms are global SCSS classes rather than
components, so the 4 kB per-component style budget is not spent on duplication.

**Fonts are self-hosted.** IBM Plex Sans (variable weight axis) and IBM Plex Mono (static 400/500)
ship from `@fontsource-variable/ibm-plex-sans` and `@fontsource/ibm-plex-mono`, emitted into the
bundle at build time. Nothing is fetched from a font host: the stack has to run with no external
network, and a Google Fonts link would break that promise. There is no variable build published for
IBM Plex Mono, which is why the two families are packaged differently.

**Interface language is Brazilian Portuguese.** The deliberate exception is the API-recorded values
above.

Full specification, plan and validation guide: [`specs/003-spa-design-system/`](specs/003-spa-design-system/).

## Trade-offs and known limitations

**The AI analysis runs synchronously inside the request.** Creating a document therefore
waits for extraction plus one model call (`AI_TIMEOUT_SECONDS`, default 15 s). This is a
deliberate simplicity choice: a task queue would add Redis and a worker to Compose and to
Kubernetes, and nothing at this scale demands it.
*Evolution path*: `analyze_document` already takes its pipeline by injection and the
analysis is already append-only and retryable, so moving it to a background job means
enqueueing instead of calling — the API contract, the model and the retry endpoint are
unchanged. The document is created before the analysis runs, so callers already handle
`latest_analysis: null`.

**The ZapSign token is stored in a plain column.** It is write-only across the API and
masked wherever it is read back (`SecretString` masks it in `str()`/`repr()`, so it cannot
leak into a log line or a traceback), and it is never present in any automation response.
Encryption at rest is *not* implemented — with database access the value is readable. For
production, put it behind a KMS-backed field or an external secret store.

**No automatic retry.** A failed ZapSign hand-off or analysis is retried by an explicit call
to `/resync/` or `/analyze/`. Scheduled retries need a scheduler, which is the same
complexity trade as above.

**The signature status is ZapSign's.** We store and display whatever they report and never
compute signature outcomes ourselves; the "terminal" statuses used by the alerts dashboard
are therefore a best-effort mapping, not a closed enum.

**Scanned PDFs are not read.** An image-only PDF is recorded as `no_text`; OCR is out of
scope.

**The risk queryset evaluates the flag in Python.** `risk` lives inside a JSON array and
JSON containment lookups are not portable across PostgreSQL and SQLite, so the newest
analysis per document is resolved in SQL and the flag checked in Python. Fine at this scale
(hundreds to low thousands of documents); it would want a generated column at a larger one.

---

## Validation

Verified against the running Docker Compose stack (PostgreSQL 16 + gunicorn + nginx):

| Area | Result |
|---|---|
| `docker compose up` | `db`, `migrate`, `backend`, `frontend` all healthy; migrations applied and the manager user seeded |
| Health probe | `GET /api/health/` → `200 {"status":"ok","checks":{"database":"ok",...}}`, no credentials |
| SPA + proxy | SPA served on `:4200`; nginx proxies `/api/` to the backend same-origin |
| Auth | JWT issued; a bad password returns `401 invalid_credentials` with no token |
| US1 organization | CRUD round-trips; the raw ZapSign token never appears in a response, only `api_token_masked`; renaming preserves the stored credential; deleting a company that owns documents returns `409 company_has_documents` |
| US2 documents | Create → `201` with signers; empty signers / bad URL / duplicate signer email all rejected `400`; edit, `resync`, and delete verified; deleting a document removed **1 signer and 4 analyses**, and the document then `404`s |
| US3 analysis | Analysis attached on create; re-running grew the history 1 → 2 with the earlier row intact; `latest_analysis` tracked the newest; history returned newest-first |
| US4 automation | Create, analyze, per-document report and summary all succeeded on an issued key alone; no credential, a SPA JWT, and a malformed key each rejected `401`; a **revoked** key rejected `403` on every endpoint; no automation response contained `api_token` |
| US5 alerts | Risk alerts raised from the latest analysis; a back-dated document also surfaced as `stalled` with `pending 9 days` |
| US6 webhook | `document.analyzed` and `document.status_changed` delivered to a real receiver with the exact contract payload and a **verified HMAC-SHA256** signature; pointed at an unreachable host, `POST /api/documents/` and `.../analyze/` still returned `201` and the failure was logged, not raised |
| Observability | One JSON log line per request with method, path, status and `elapsed_ms`; the inbound `X-Correlation-ID` is honoured, echoed, and present on the log record; no ZapSign token, seed password or webhook secret appears anywhere in the logs |
| Test suites | backend **242 passed**, 94% coverage; frontend **74 passed**, 86% coverage; `ruff`, `mypy` and `tsc` all clean |

**Not executed: the Kubernetes rollout.** No cluster was available on the validation
machine. Both Kustomize overlays render (11 resources local, 13 prod) and were checked
structurally — namespace, probes on `/api/health/`, per-workload images, non-root security
context, resource requests/limits, ingress routing, migrate-Job restart policy and
placeholder-only Secret — but `kubectl apply -k deploy/k8s/overlays/local` and the rollout
have **not** been run. Treat the manifests as reviewed, not proven.


## Deployment

```bash
kubectl apply -k deploy/k8s/overlays/local
kubectl -n docsign rollout status deploy/backend deploy/frontend
```

`deploy/k8s/base/` holds the Deployments, Services, ConfigMap, Secret placeholder, Ingress,
a migrate Job and the PostgreSQL StatefulSet, with liveness/readiness probes on
`/api/health/`; `overlays/local` and `overlays/prod` carry the environment differences.
Both images are multi-stage and run as non-root.

Secrets (`DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`, `OPENAI_API_KEY`, `N8N_WEBHOOK_SECRET`)
come from environment variables / Kubernetes Secrets and are never committed.
`deploy/.env.example` is the current list.

## Bonus features

- **Alerts dashboard** (`/api/alerts/`, SPA `/alerts`) — documents pending past
  `ALERT_STALLED_DAYS`, and documents whose latest analysis carries a risk insight.
- **Outbound webhook** — on a signature-status change or a risk-bearing analysis, a
  contract-shaped event is POSTed to `N8N_WEBHOOK_URL` after the transaction commits,
  optionally HMAC-signed. Delivery failure can never affect the document operation. An
  example workflow ships in [`deploy/n8n/`](deploy/n8n/).

## Project documentation

`specs/001-document-signature-management/` holds the specification, the implementation plan
and its architecture stance, the data model, the API and gateway contracts, the research
decisions, the quickstart validation guide and the task breakdown.
