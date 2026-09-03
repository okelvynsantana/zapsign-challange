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
each with a thin DDD layering (pure typed domain rules → application services → DRF I/O). All
external providers (ZapSign, the LLM, PDF extraction, the outbound webhook) sit behind typed
gateway interfaces so domain code never touches an SDK or HTTP client. PostgreSQL with UUID PKs and
migrations. Angular SPA. Everything containerised with multi-stage Dockerfiles, a one-command
`docker compose` local stack, and Kustomize-based Kubernetes manifests. GitHub Actions runs lint,
type-check, backend and frontend test suites (with coverage gates), and image builds.

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
| I. Clean Architecture & Dependency Inversion | Domain/application/infra layers separated; no SDK/HTTP in domain or application code; every external provider behind an interface; six domain-scoped Django apps | Each app has `domain/` (pure, typed dataclasses + rules), `services.py` (use cases), and DRF `serializers.py`/`views.py`. `integrations/` holds `ZapSignGateway`, `AnalysisProvider`, `PdfTextExtractor`, `WebhookNotifier` as ABCs with concrete impls; domain/services depend on the ABCs. Apps: `companies`, `documents`, `signers`, `integrations`, `automation`, `core`. **PASS** |
| II. Test-First for Critical Logic (NON-NEGOTIABLE) | TDD on ZapSign client, AI pipeline, status rules; external APIs mocked; CI never calls third parties; ≥80% coverage on primary routes; Pytest + Jest | `tasks.md` will order tests before impl for every integration/business-rule unit. `respx`/`responses` mock ZapSign & OpenAI; a fake `AnalysisProvider`/`ZapSignGateway` used in service tests. `pytest --cov` with `--cov-fail-under=80` scoped to primary flow packages in CI. Jest for frontend. **PASS** |
| III. Simplicity First (KISS / YAGNI) | Simplest solution that meets the requirement; no async/queue/cache/extra layers unless required; conscious trade-offs documented in README | Synchronous AI call (no Celery/Redis). Single PDF library (`pypdf`). Kustomize (no Helm). No caching layer. DDD layering kept thin — no repository pattern over the ORM; domain rules extracted only where they carry real logic. README records the sync-AI trade-off and its evolution path. **PASS** |
| IV. Resilient External Integrations | Local CRUD survives ZapSign/LLM failure; document persisted before external calls; explicit pending/failed state; bounded configurable timeouts; retryable | `DocumentService.create` writes the row (`provider_status=pending_integration`) before any outbound call. ZapSign failure → `provider_status=failed`, retry via `POST /api/documents/{id}/resync/`. LLM failure → `DocumentAnalysis(state=failed, error_reason=...)`, retry via `POST /api/documents/{id}/analyze/`. All outbound calls use `httpx` timeouts from settings. **PASS** |
| V. Secure, Observable REST API | Auth on every external endpoint (session/JWT for frontend, revocable API key for automation); RESTful on DRF; public `/api/health/` checking DB + integrations; structured logs with timing on integration calls + primary routes | `simplejwt` for the SPA; `djangorestframework-api-key` (`Authorization: Api-Key <key>`) for `automation` endpoints; ZapSign token never serialized. `core.health` view checks DB and (best-effort) provider reachability, unauthenticated. `core.middleware.RequestTimingLogger` + a gateway logging decorator emit JSON logs with route/provider, status, `elapsed_ms`. **PASS** |
| VI. Explicit Domain Data Model | UUID PKs everywhere; PostgreSQL; all schema via migrations; Document→Signer cascade delete; `DocumentAnalysis` append-only with most-recent-as-current | `UUIDField(primary_key=True, default=uuid4, editable=False)` on every model. `Signer.document` FK `on_delete=CASCADE`. Analyses are insert-only; read endpoints return latest by `created_at`; history via `GET /api/documents/{id}/analyses/`. See [data-model.md](./data-model.md). **PASS** |
| VII. Reproducible & Deploy-Ready Environment | Whole stack dockerized, `docker compose up` one command; multi-stage k8s-ready Dockerfiles; k8s manifests or documented cut; README enables full setup; reactive frontend, no reload | `deploy/docker-compose.yml` (postgres + backend + frontend + migrate job). Multi-stage `backend/Dockerfile` and `frontend/Dockerfile` (non-root, distroless/nginx runtime). `deploy/k8s/` Kustomize base + `local`/`prod` overlays with probes on `/api/health/`. `quickstart.md` + README cover setup/tests/endpoints. Angular signals + `HttpClient` re-fetch on mutation, no navigation reload. **PASS** |
| Technology & Architecture Constraints | Fixed stack: Django+DRF, PostgreSQL, Angular, direct OpenAI (no LangChain), `pypdf`/`pdfplumber`, Pytest/Jest, Docker/k8s, SOLID/DDD-light/KISS; secrets via env/Secret; keep `.env.example` current | Matches exactly. Added by user input and recorded here: full type hints + `mypy` in CI, `ruff`, GitHub Actions pipeline — all consistent with the constraints (no deviation, no amendment required). `deploy/.env.example` maintained. **PASS** |

**Result**: All gates pass. No violations → Complexity Tracking not required.

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
    │   ├── domain/               # shared value objects, typed base entities, enums
    │   ├── health.py             # GET /api/health/ (DB + integrations, unauthenticated)
    │   ├── logging.py            # JSON formatter, gateway logging decorator
    │   ├── middleware.py         # per-request timing + structured access log
    │   ├── pagination.py
    │   └── tests/
    ├── companies/
    │   ├── domain/
    │   │   ├── entities.py       # Company entity (frozen dataclass, typed)
    │   │   └── rules.py          # deletion guard, credential masking rules
    │   ├── models.py             # Company ORM model (UUID PK)
    │   ├── services.py           # CompanyService use cases
    │   ├── serializers.py        # api_token write-only / masked
    │   ├── views.py              # DRF viewset
    │   ├── urls.py
    │   ├── migrations/
    │   └── tests/                # unit (domain) + api (viewset) + service tests
    ├── documents/
    │   ├── domain/
    │   │   ├── entities.py       # Document, DocumentAnalysis entities
    │   │   ├── status.py         # provider_status / signature status enums + transitions
    │   │   └── rules.py          # create-before-call rule, latest-analysis selection
    │   ├── models.py             # Document, DocumentAnalysis ORM (UUID PK, cascade)
    │   ├── services.py           # DocumentService: create, resync, analyze, reports
    │   ├── serializers.py
    │   ├── views.py              # documents viewset + analyze/analyses/resync/report actions
    │   ├── urls.py
    │   ├── migrations/
    │   └── tests/
    ├── signers/
    │   ├── domain/
    │   │   ├── entities.py       # Signer entity
    │   │   └── rules.py          # email/name validation, duplicate-email policy
    │   ├── models.py             # Signer ORM (FK Document on_delete=CASCADE)
    │   ├── services.py
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
    │   │   ├── provider.py       # AnalysisProvider ABC + AnalysisResult dataclass
    │   │   ├── openai_provider.py# OpenAIAnalysisProvider (direct SDK)
    │   │   ├── clause_checker.py # regex/keyword missing-clause reinforcement
    │   │   ├── pipeline.py       # extract → LLM → regex merge → AnalysisResult
    │   │   └── tests/            # mocked OpenAI (TDD)
    │   ├── pdf/
    │   │   ├── extractor.py      # PdfTextExtractor ABC + PypdfTextExtractor impl
    │   │   └── tests/
    │   └── config.py             # typed integration settings (timeouts, model, base URLs)
    └── automation/
        ├── auth.py               # API-key auth class + permission
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
each domain app carries a thin `domain/` (pure, typed) + `services.py` + DRF I/O layering, while
`integrations/` is infrastructure-only and holds every third-party gateway behind an ABC. Frontend
under `frontend/` as an Angular SPA. All deploy assets under `deploy/` (Compose + Kustomize). CI
under `.github/workflows/`. This is the layout referenced by `data-model.md`, the contracts, and
`quickstart.md`.

## Complexity Tracking

No Constitution Check violations. Section intentionally empty.
