# Implementation Plan: Document & Signature Management System

**Branch**: `001-document-signature-management` | **Date**: 2026-09-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-document-signature-management/spec.md`

## Summary

Build, greenfield, an internal system that lets a non-technical manager manage an organization
profile, documents, and signers through a reactive single-page app; on document creation the system
persists locally first, then submits the document to the ZapSign sandbox and stores the returned
identifiers/status, then runs a synchronous AI content analysis (summary, missing clauses, insights)
that is kept as append-only history. Authenticated REST endpoints let internal automation create
documents, re-run analysis, and pull per-document and aggregated reports. Bonus scope adds an alerts
dashboard and an outbound webhook to an automation platform.

Technical approach: a monorepo with a Django + Django REST Framework backend split into six
domain-scoped apps (`companies`, `documents`, `signers`, `integrations`, `automation`, `core`),
written **idiomatically for Django** — models are the domain layer (Active Record: business rules
as model methods, properties and `clean()`; reusable query logic as custom `QuerySet`/`Manager`
methods; enums as `TextChoices`), DRF serializers own validation and representation, and viewsets
stay thin. Decoupling is applied where it buys something rather than uniformly: every external
provider (ZapSign, the LLM, PDF extraction, the outbound webhook) sits behind a typed gateway
interface with a fake, so no model, service or view ever imports an SDK or issues HTTP directly;
and the few use cases that span several models *and* an external call (document create / resync /
analyze) live in a thin `services.py` of plain typed functions that receive their gateways by
injection. PostgreSQL with UUID PKs and migrations. Angular SPA. Everything containerised with
multi-stage Dockerfiles, a one-command `docker compose` local stack, and Kustomize-based Kubernetes
manifests. GitHub Actions runs lint, type-check, backend and frontend test suites (with coverage
gates), and image builds.

## Technical Context

**Language/Version**: Backend Python 3.12; Frontend TypeScript 5.x on Node.js 20 LTS

**Primary Dependencies**:
- Backend: Django 5.x LTS, Django REST Framework, `djangorestframework-simplejwt` (internal user
  auth), `djangorestframework-api-key` (per-integration API keys), `openai` SDK (direct, no
  LangChain), `pypdf` (PDF text extraction), `httpx` (outbound calls to ZapSign / webhook),
  `python-json-logger` (structured logs), `psycopg[binary]`
- Backend tooling: `pytest`, `pytest-django`, `pytest-cov`, `factory-boy`, `respx`/`responses`
  (HTTP mocking), `ruff` (lint + format), `mypy` with `django-stubs` + `djangorestframework-stubs`
- Frontend: Angular 19 (standalone components, reactive forms, signals), RxJS, Angular HttpClient;
  tests with Jest (`jest-preset-angular`)

**Storage**: PostgreSQL 16; schema via Django migrations; all domain PKs are UUID v4

**Testing**: `pytest` (backend, TDD on integration/business logic, external providers mocked, ≥80%
coverage on primary flows enforced in CI); Jest (frontend components and services)

**Target Platform**: Linux containers; local via Docker Compose; deploy to Kubernetes (Deployment,
Service, ConfigMap/Secret, Ingress, liveness/readiness probes on `/api/health/`)

**Project Type**: Web application — Angular SPA frontend + Django REST API backend (monorepo)

**Performance Goals** (from spec Success Criteria):
- Document form submit → confirmed local save in < 5 s (excluding AI latency)
- AI analysis returns summary + missing topics + insights within 15 s for ≥ 95 % of text-bearing PDFs
- List views reflect create/edit/delete in < 1 s with no full page reload
- New developer: clone → running stack → primary flows exercised in < 10 min

**Constraints**:
- AI analysis runs synchronously inside the create / re-analyze request with a configurable timeout
  (default 15 s); no task queue (KISS) — asynchronous processing is a documented future evolution
- A failure or timeout of ZapSign or the LLM MUST NOT roll back the local document or each other
- ZapSign `api_token` is never returned by any serializer or exposed to automation callers
- `/api/health/` is unauthenticated (infra probes must not need app credentials)
- Structured log entry per external-dependency call and per primary route, with status + elapsed ms
- All backend public methods and domain entities carry explicit type hints; `mypy` runs in CI

**Scale/Scope**: Single-tenant in practice (one organization row), a handful of internal users,
low write volume (hundreds–low thousands of documents); horizontally scalable via stateless backend
pods behind k8s. Scope: 6 backend apps, ~6 domain entities, ~15 REST endpoints, ~5 Angular feature
areas, 6 prioritized user stories (2×P1, 2×P2, 2×P3 bonus).

**Resolved unknowns** (see [research.md](./research.md)): Python/Django/Angular versions, internal
auth mechanism, API-key mechanism, LLM model choice, PDF library choice, `mypy` strictness level,
structured-logging approach, k8s manifest tooling, CI pipeline shape. No open NEEDS CLARIFICATION.

## Constitution Check

*GATE: evaluated against `.specify/memory/constitution.md` v1.0.0. Must pass before Phase 0 and be
re-checked after Phase 1.*

| Principle | Gate | Plan compliance |
|-----------|------|-----------------|
| I. Clean Architecture & Dependency Inversion | Domain/application/infra concerns separated; no SDK/HTTP in domain or application code; every external provider behind an interface; six domain-scoped Django apps | Concerns are separated by *role*, using Django's own seams rather than a parallel entity layer: business rules and invariants on the models (methods, properties, `clean()`, `TextChoices`), reusable query logic in `querysets.py`, multi-model-plus-external-call use cases in a thin `services.py`, HTTP/validation in DRF `serializers.py`/`views.py`, and third-party access confined to `integrations/`. `integrations/` holds `ZapSignGateway`, `AnalysisProvider`, `PdfTextExtractor`, `WebhookNotifier` as ABCs with real + fake impls; models, querysets, services and views depend only on the ABCs and never import `httpx`, `openai` or `pypdf`. Apps: `companies`, `documents`, `signers`, `integrations`, `automation`, `core`. See "Architecture Stance" below for the reading of this principle. **PASS (with a recorded interpretation)** |
| II. Test-First for Critical Logic (NON-NEGOTIABLE) | TDD on ZapSign client, AI pipeline, status rules; external APIs mocked; CI never calls third parties; ≥80% coverage on primary routes; Pytest + Jest | `tasks.md` will order tests before impl for every integration/business-rule unit. `respx`/`responses` mock ZapSign & OpenAI; a fake `AnalysisProvider`/`ZapSignGateway` used in service tests. `pytest --cov` with `--cov-fail-under=80` scoped to primary flow packages in CI. Jest for frontend. **PASS** |
| III. Simplicity First (KISS / YAGNI) | Simplest solution that meets the requirement; no async/queue/cache/extra layers unless required; conscious trade-offs documented in README | Synchronous AI call (no Celery/Redis). Single PDF library (`pypdf`). Kustomize (no Helm). No caching layer. **No repository pattern and no dataclass mirror of the ORM** — the ORM *is* the persistence abstraction and Django's `QuerySet` *is* the query abstraction; adding a parallel entity layer would be the "additional abstraction layer" this principle forbids. `services.py` exists only for the three use cases that genuinely orchestrate multiple models plus an external call; single-model CRUD goes straight through the viewset/serializer. README records the sync-AI trade-off and its evolution path. **PASS** |
| IV. Resilient External Integrations | Local CRUD survives ZapSign/LLM failure; document persisted before external calls; explicit pending/failed state; bounded configurable timeouts; retryable | `create_document` writes the row (`provider_status=pending_integration`) before any outbound call. ZapSign failure → `provider_status=failed`, retry via `POST /api/documents/{id}/resync/`. LLM failure → `DocumentAnalysis(state=failed, error_reason=...)`, retry via `POST /api/documents/{id}/analyze/`. All outbound calls use `httpx` timeouts from settings. **PASS** |
| V. Secure, Observable REST API | Auth on every external endpoint (session/JWT for frontend, revocable API key for automation); RESTful on DRF; public `/api/health/` checking DB + integrations; structured logs with timing on integration calls + primary routes | `simplejwt` for the SPA; `djangorestframework-api-key` (`Authorization: Api-Key <key>`) for `automation` endpoints; ZapSign token never serialized. `core.health` view checks DB and (best-effort) provider reachability, unauthenticated. `core.middleware.RequestTimingLogger` + a gateway logging decorator emit JSON logs with route/provider, status, `elapsed_ms`. **PASS** |
| VI. Explicit Domain Data Model | UUID PKs everywhere; PostgreSQL; all schema via migrations; Document→Signer cascade delete; `DocumentAnalysis` append-only with most-recent-as-current | `UUIDField(primary_key=True, default=uuid4, editable=False)` on every model. `Signer.document` FK `on_delete=CASCADE`. Analyses are insert-only; read endpoints return latest by `created_at`; history via `GET /api/documents/{id}/analyses/`. See [data-model.md](./data-model.md). **PASS** |
| VII. Reproducible & Deploy-Ready Environment | Whole stack dockerized, `docker compose up` one command; multi-stage k8s-ready Dockerfiles; k8s manifests or documented cut; README enables full setup; reactive frontend, no reload | `deploy/docker-compose.yml` (postgres + backend + frontend + migrate job). Multi-stage `backend/Dockerfile` and `frontend/Dockerfile` (non-root, distroless/nginx runtime). `deploy/k8s/` Kustomize base + `local`/`prod` overlays with probes on `/api/health/`. `quickstart.md` + README cover setup/tests/endpoints. Angular signals + `HttpClient` re-fetch on mutation, no navigation reload. **PASS** |
| Technology & Architecture Constraints | Fixed stack: Django+DRF, PostgreSQL, Angular, direct OpenAI (no LangChain), `pypdf`/`pdfplumber`, Pytest/Jest, Docker/k8s, SOLID/DDD-light/KISS; secrets via env/Secret; keep `.env.example` current | Matches exactly. Added by user input and recorded here: full type hints + `mypy` in CI, `ruff`, GitHub Actions pipeline — all consistent with the constraints (no deviation, no amendment required). `deploy/.env.example` maintained. **PASS** |

**Result**: All gates pass. No violations → Complexity Tracking not required.

## Architecture Stance

*Recorded interpretation of Constitution Principle I, referenced from the Constitution
Check table above.*

The constitution requires domain, application and infrastructure concerns to be
**separated**, and requires every external provider to sit behind an interface. It does
not prescribe *where* the domain lives, and Principle III forbids abstraction layers a
requirement does not demand. This project therefore separates by **role**, using Django's
own seams rather than a parallel entity layer:

| Concern | Where it lives | Why |
|---|---|---|
| Business rules and invariants | The model (`clean()`, methods, properties, `TextChoices`) | Active Record is Django's design. Rules hold for the API, the admin, a management command and a shell session alike, because they are attached to the object itself. |
| Reusable query logic | `querysets.py` (custom `QuerySet` + a named `Manager`) | `QuerySet` *is* the query abstraction; a repository over it would restate it with fewer features. |
| Use cases spanning several models **and** an external call | `services.py` — plain typed functions, gateways injected | These genuinely orchestrate: document create / resync / analyze. Single-model CRUD does not, and goes straight through viewset + serializer. |
| HTTP shape and validation | DRF `serializers.py` / `views.py` | Where DRF puts them. Viewsets stay thin. |
| Third-party access | `apps/integrations/` — one ABC per provider, plus a real and a fake implementation | This is the decoupling that pays: no model, queryset, service or view imports `httpx`, `openai` or `pypdf`, and every failure path is testable with a fake. |

**What this stance deliberately rejects**: a repository pattern over the ORM, and a
frozen-dataclass mirror of every model. Both restate what Django already provides, and
adding them is the "additional abstraction layer" Principle III forbids. Frozen dataclasses
*are* used where they earn their place — provider DTOs (`ZapSignCreateRequest`,
`ProviderAnalysis`, `AnalysisResult`) and the derived `Alert` view — because those cross a
boundary or have no table behind them.

**Consequence for the data model**: entities below are Django models; the "Domain
dataclass" lines in `data-model.md` describe behaviour that is implemented as model
methods and properties (`Company.masked_token`, `Document.can_resync()`,
`Document.mark_submitted()`, `Signer.normalized_email`, `DocumentAnalysis.has_risk_insight`).


## Project Structure

### Documentation (this feature)

```text
specs/001-document-signature-management/
├── plan.md              # This file (/speckit-plan)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── rest-api.md          # External REST endpoints: routes, schemas, auth, errors
│   ├── openapi.yaml         # Machine-readable REST contract
│   ├── analysis-provider.md # Internal AnalysisProvider gateway interface
│   ├── zapsign-gateway.md   # Internal ZapSign gateway interface
│   └── webhook-outbound.md  # Outbound automation webhook payload contract
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml                # deps, ruff, mypy, pytest, coverage config
├── manage.py
├── Dockerfile                    # multi-stage, non-root, k8s-ready
├── config/                       # Django project
│   ├── settings/
│   │   ├── base.py               # typed settings, env-driven
│   │   ├── local.py
│   │   └── prod.py
│   ├── urls.py                   # mounts /api/ + /api/health/
│   ├── asgi.py
│   └── wsgi.py
└── apps/
    ├── core/
    │   ├── models.py             # abstract UUIDModel / TimeStampedModel bases
    │   ├── values.py             # SecretString value object (credential masking)
    │   ├── exceptions.py         # DRF handler -> {detail, code, fields}
    │   ├── schema.py             # response serializers for hand-written views
    │   ├── health.py             # GET /api/health/ (DB + integrations, unauthenticated)
    │   ├── logging.py            # JSON formatter, gateway logging decorator
    │   ├── middleware.py         # per-request timing + structured access log
    │   ├── pagination.py
    │   └── tests/
    ├── companies/
    │   ├── models.py             # Company (UUID PK, masked_token, name invariant)
    │   ├── querysets.py          # CompanyQuerySet (with_document_count, deletable)
    │   ├── serializers.py        # api_token write-only / masked
    │   ├── views.py              # DRF viewset; ProtectedError -> 409
    │   ├── urls.py
    │   ├── migrations/
    │   └── tests/                # model rules + api + delete guard + factories
    ├── documents/
    │   ├── status.py             # ProviderStatus TextChoices + pure transition guard
    │   ├── models.py             # Document, DocumentAnalysis (UUID PK, cascade, rules)
    │   ├── querysets.py          # DocumentQuerySet (latest analysis, risk, stalled)
    │   ├── services.py           # create_document / resync_document / analyze_document
    │   ├── reports.py            # per-document + aggregated report aggregation
    │   ├── alerts.py             # derived stalled/risk alerts (bonus)
    │   ├── serializers.py
    │   ├── views.py              # documents viewset + analyze/analyses/resync/report actions
    │   ├── urls.py
    │   ├── migrations/
    │   └── tests/
    ├── signers/
    │   ├── models.py             # Signer (FK Document CASCADE, unique email per document)
    │   ├── querysets.py          # SignerQuerySet (for_document)
    │   ├── serializers.py
    │   ├── views.py
    │   ├── urls.py
    │   ├── migrations/
    │   └── tests/
    ├── integrations/             # infrastructure only — isolated from domain apps
    │   ├── zapsign/
    │   │   ├── gateway.py        # ZapSignGateway ABC + typed request/response dataclasses
    │   │   ├── client.py         # HttpZapSignGateway (httpx impl)
    │   │   └── tests/            # respx-mocked contract tests (TDD)
    │   ├── analysis/
    │   │   ├── provider.py       # AnalysisProvider ABC + ProviderAnalysis dataclass
    │   │   ├── results.py        # AnalysisResult + Insight (pipeline output)
    │   │   ├── openai_provider.py# OpenAIAnalysisProvider (direct SDK)
    │   │   ├── clause_checker.py # regex/keyword missing-clause reinforcement
    │   │   ├── pipeline.py       # extract → LLM → regex merge → AnalysisResult
    │   │   └── tests/            # mocked OpenAI (TDD)
    │   ├── pdf/
    │   │   ├── extractor.py      # PdfTextExtractor ABC + PypdfTextExtractor impl
    │   │   └── tests/
    │   └── config.py             # typed integration settings (timeouts, model, base URLs)
    └── automation/
        ├── auth.py               # API-key auth class + permissions
        ├── schema.py             # OpenAPI description of the API-key scheme
        ├── views.py              # document-create, analyze, per-doc report, summary report
        ├── webhook.py            # WebhookNotifier ABC + HttpWebhookNotifier + event builders
        ├── serializers.py
        ├── urls.py
        └── tests/

frontend/
├── package.json
├── Dockerfile                    # multi-stage build → nginx static runtime
├── jest.config.ts
├── src/
│   ├── app/
│   │   ├── core/
│   │   │   ├── api/              # typed API client services (Company, Document, Signer, Report)
│   │   │   ├── auth/             # JWT interceptor, login, token storage
│   │   │   └── models/           # TypeScript interfaces mirroring API schemas
│   │   ├── companies/            # list + form (reactive, signal-based store)
│   │   ├── documents/            # list + create form + detail (analysis view, resync, re-analyze)
│   │   ├── signers/              # inline signer management within document form/detail
│   │   ├── reports/              # aggregated report view
│   │   ├── alerts/               # bonus: alerts dashboard
│   │   └── shared/               # UI primitives, form helpers, error display
│   └── environments/
└── src/test/                     # Jest setup

deploy/
├── docker-compose.yml            # postgres + backend + frontend + one-shot migrate
├── .env.example                  # every required env var, documented
└── k8s/
    ├── base/                     # namespace, backend deploy/svc, frontend deploy/svc,
    │                             # postgres statefulset, configmap, secret (templated),
    │                             # ingress, probes → /api/health/
    └── overlays/
        ├── local/
        └── prod/

.github/
└── workflows/
    ├── backend.yml               # ruff + mypy + pytest (postgres service) + coverage gate
    ├── frontend.yml              # eslint + jest + build
    └── images.yml                # build (and optionally push) backend + frontend images

README.md                         # setup, tests, endpoint docs, AI logic, architecture rationale
```

**Structure Decision**: Web-application monorepo. Backend under `backend/` as a Django project
(`config/`) with six domain-scoped apps under `backend/apps/` (Constitution Principle I / RNF13);
each domain app keeps its rules on the models plus `querysets.py`, a thin `services.py` only
where a use case spans several models and an external call, and DRF I/O on top, while
`integrations/` is infrastructure-only and holds every third-party gateway behind an ABC. Frontend
under `frontend/` as an Angular SPA. All deploy assets under `deploy/` (Compose + Kustomize). CI
under `.github/workflows/`. This is the layout referenced by `data-model.md`, the contracts, and
`quickstart.md`.

## Complexity Tracking

No Constitution Check violations. Section intentionally empty.
