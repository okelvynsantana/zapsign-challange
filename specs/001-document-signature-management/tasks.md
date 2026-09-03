---
description: "Task list for Document & Signature Management System"
---

# Tasks: Document & Signature Management System

**Input**: Design documents from `specs/001-document-signature-management/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: INCLUDED. The constitution (`.specify/memory/constitution.md`) makes TDD **non-negotiable**
for the integration and business-rule components (ZapSign gateway, AI pipeline, status rules) and
requires automated tests on primary routes with ≥80% coverage. Test tasks below are scoped to those
areas — trivial field-level CRUD is not separately unit-tested.

**Organization**: Tasks are grouped by user story (spec.md priorities). Each story phase is an
independently testable increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1–US6 for user-story phases; no label for Setup / Foundational / Polish
- File paths are relative to repo root

## Path Conventions

Monorepo per [plan.md](./plan.md): `backend/` (Django project `config/` + apps under `backend/apps/`),
`frontend/` (Angular), `deploy/` (Compose + Kustomize), `.github/workflows/` (CI).

## Architecture stance (drives every task below)

Per [plan.md](./plan.md) Constitution Check (Principles I and III), the backend is written
**idiomatically for Django**:

- **Models are the domain layer** (Active Record): invariants in `clean()`, business rules as model
  methods/properties, enums as `TextChoices`. There is **no** parallel frozen-dataclass mirror of
  the ORM and **no** repository pattern — the ORM is the persistence abstraction.
- **Reusable query logic lives in `querysets.py`** per app (custom `QuerySet`/`Manager`).
- **`services.py` holds only the use cases that span several models *and* an external call**
  (document create / resync / analyze) as plain typed functions receiving their gateways by
  injection. Single-model CRUD goes straight through viewset + serializer.
- **Every third-party provider is an ABC in `integrations/`** with a real and a fake implementation;
  models, querysets, services and views never import `httpx`, `openai` or `pypdf`. Provider DTOs
  (`ZapSignCreateRequest`, `ProviderAnalysis`, `AnalysisResult`, …) are frozen dataclasses and live
  in `integrations/`, not in the domain apps.

> `data-model.md` and `contracts/analysis-provider.md` still describe the earlier
> `<app>/domain/entities.py` dataclass layout; T114 reconciles that wording. Where they disagree
> with this section, **this section (and plan.md) wins** for implementation purposes.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project skeleton, tooling, container and CI scaffolding.

**Status**: complete — delivered by commit `cbca089` ("chore: scaffold monorepo, containers, CI and
deploy assets").

- [X] T001 Create monorepo directory structure (`backend/`, `frontend/`, `deploy/`, `.github/workflows/`, `README.md` stub) per [plan.md](./plan.md) "Source Code" tree
- [X] T002 Initialize Django project in `backend/`: `backend/pyproject.toml` (Django 5.x LTS, DRF, `djangorestframework-simplejwt`, `djangorestframework-api-key`, `openai`, `pypdf`, `httpx`, `psycopg[binary]`, `python-json-logger`), `backend/manage.py`, `backend/config/{__init__,urls,wsgi,asgi}.py`, `backend/config/settings/{base,local,prod,env}.py`, six empty apps under `backend/apps/`
- [X] T003 [P] Configure backend tooling in `backend/pyproject.toml`: `ruff` (lint+format), `mypy` + `django-stubs` + `djangorestframework-stubs` (pragmatic-strict per [research.md](./research.md) §9), `pytest`/`pytest-django`/`pytest-cov`/`factory-boy`/`respx` with `fail_under = 80`
- [X] T004 [P] Initialize Angular 19 app in `frontend/` (standalone components, routing) with Jest via `jest-preset-angular`: `frontend/package.json`, `frontend/jest.config.ts`, `frontend/src/test/setup.ts`, `frontend/eslint.config.js`
- [X] T005 [P] Create `backend/Dockerfile` (multi-stage, non-root, `gunicorn` runtime, k8s-ready) per [research.md](./research.md) §12
- [X] T006 [P] Create `frontend/Dockerfile` (multi-stage build → nginx static runtime) + `frontend/nginx.conf`
- [X] T007 [P] Create `deploy/.env.example` documenting every variable (`POSTGRES_*`, `DJANGO_*`, `SEED_*`, `ZAPSIGN_*`, `OPENAI_API_KEY`, `AI_*`, `PDF_*`, `ALERT_STALLED_DAYS`, `N8N_WEBHOOK_*`, `WEBHOOK_*`, `PUBLIC_BASE_URL`, `FRONTEND_API_BASE_URL`)
- [X] T008 [P] Create `deploy/docker-compose.yml` with services `db` (postgres:16), `migrate` (one-shot), `backend` (:8000), `frontend` (:4200), healthchecks and `.env` wiring
- [X] T009 [P] Create `.github/workflows/backend.yml`: setup Python 3.12 → install → `ruff check` + `ruff format --check` → `mypy` → `pytest --cov --cov-fail-under=80` against a `postgres:16` service; no third-party network
- [X] T010 [P] Create `.github/workflows/frontend.yml`: setup Node 20 → `npm ci` → `eslint` → `jest --coverage` → `npm run build`
- [X] T011 [P] Create `.github/workflows/images.yml`: Buildx build of backend + frontend images with layer cache; push to GHCR only on default branch / tags

**Checkpoint**: `docker compose -f deploy/docker-compose.yml config` validates; `manage.py check`
passes; empty test suites run.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Cross-cutting infrastructure every user story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T012 Expand `backend/config/settings/base.py` from env (typed helpers in `config/settings/env.py`): PostgreSQL-only `DATABASES`, `THIRD_PARTY_APPS` (`rest_framework`, `rest_framework_simplejwt`, `rest_framework_api_key`, `corsheaders`, `drf_spectacular`) and `LOCAL_APPS` (the six `apps.*`), `REST_FRAMEWORK` block (JWT default auth, `IsAuthenticated` default permission, `DEFAULT_PAGINATION_CLASS`, `EXCEPTION_HANDLER`), `SIMPLE_JWT`, CORS, `LOGGING`, middleware registration
- [X] T013 Establish shared model/value primitives in `backend/apps/core/`: `models.py` with abstract `UUIDModel` (UUID v4 PK, non-editable) and `TimeStampedModel` (`created_at`, `last_updated_at`), `values.py` with the `SecretString` value object (masking helper), and **delete the now-unused `domain/` packages** (`backend/apps/{core,companies,documents,signers}/domain/`) per the Architecture stance above
- [X] T014 [P] Implement structured logging in `backend/apps/core/logging.py`: `python-json-logger` formatter, `log_gateway_call` decorator (provider, operation, outcome, `elapsed_ms`, secret-redaction hook) per [research.md](./research.md) §10
- [X] T015 [P] Implement `backend/apps/core/middleware.py` `RequestTimingLogger` (method, path, status, `elapsed_ms`, correlation id) and register it in `backend/config/settings/base.py`
- [X] T016 [P] Implement DRF exception handler in `backend/apps/core/exceptions.py` producing the standard error body `{detail, code, fields}` from [contracts/rest-api.md](./contracts/rest-api.md), including `ProtectedError` → `409 company_has_documents`; wire `EXCEPTION_HANDLER` in settings
- [X] T017 [P] Implement `backend/apps/core/pagination.py` `DefaultPageNumberPagination` (`page`, `page_size` 1–100, default 20)
- [X] T018 Implement health check in `backend/apps/core/health.py` + `backend/apps/core/urls.py`: `GET /api/health/` unauthenticated, DB check → 200/503, best-effort time-boxed `zapsign`/`openai` reachability checks that never fail the endpoint (FR-027, [research.md](./research.md) §11)
- [X] T019 [P] `backend/apps/core/tests/test_health.py`: 200 when DB ok; 503 when the DB check raises; provider-check failure keeps 200; endpoint requires no auth
- [X] T020 Implement typed integration settings in `backend/apps/integrations/config.py` (frozen dataclass reading `ZAPSIGN_*`, `AI_*`, `PDF_*`, `WEBHOOK_*`, `N8N_*` with the defaults documented in the contracts)
- [X] T021 Wire root URLconf `backend/config/urls.py`: mount `/api/health/`, `/api/auth/`, and the per-app routers under `/api/`
- [X] T022 Implement JWT auth endpoints (`POST /api/auth/token/`, `POST /api/auth/token/refresh/`) via `simplejwt` in `backend/config/urls.py` + settings; failed login maps to the `invalid_credentials` error body
- [X] T023 [P] Create `backend/apps/core/management/commands/seed_user.py` creating the internal manager user idempotently from `SEED_USERNAME`/`SEED_PASSWORD`
- [X] T024 Create `backend/apps/automation/auth.py`: API-key authentication class (`Authorization: Api-Key <key>`) + `HasApiKey` permission rejecting missing/malformed/revoked/expired keys with no body data (FR-023); a JWT is **not** accepted by this class
- [X] T025 [P] Create `backend/apps/automation/management/commands/{create_api_key,revoke_api_key}.py` (print the plaintext key once on create; revoke by prefix)
- [X] T026 [P] `backend/apps/automation/tests/test_api_key_auth.py`: valid key passes; missing/malformed/revoked/expired → 401/403 with no data; a JWT is rejected by the API-key permission
- [X] T027 [P] Scaffold Angular core in `frontend/src/app/core/`: `api/http.service.ts` (base URL from `environments/`, error mapping), `auth/auth.interceptor.ts` (Bearer), `auth/auth.service.ts` + token storage, `auth/login.component.ts`, `models/index.ts`, routing shell in `frontend/src/app/app.routes.ts`, shared error component in `frontend/src/app/shared/`
- [X] T028 Verify the end-to-end skeleton: `docker compose -f deploy/docker-compose.yml up` brings `db`+`migrate`+`backend`+`frontend` healthy; `curl localhost:8000/api/health/` returns 200; the Angular login page loads and can obtain a JWT

**Checkpoint**: Foundation ready — user stories can now proceed.

---

## Phase 3: User Story 1 - Organization profile & signature credentials (Priority: P1) 🎯 MVP

**Goal**: Manager can create, view, update, and delete the organization profile holding the ZapSign
credential; the credential is never returned in full; deletion is blocked while documents exist.

**Independent Test**: Create a profile with name + `api_token`; confirm it lists with only
`api_token_masked`; edit the name without resending the token; delete it (and, after US2, confirm a
profile with a document returns `409`).

### Tests for User Story 1 ⚠️ (write first, must fail)

- [X] T029 [P] [US1] `backend/apps/companies/tests/test_models.py`: `Company` model rules — `masked_token` property masks all but the last 4 chars, `clean()` rejects a blank/whitespace `name`, `api_token` round-trips through `SecretString`, UUID PK is generated
- [X] T030 [P] [US1] `backend/apps/companies/tests/test_api.py`: CRUD round-trip on `/api/companies/`; no response ever contains `api_token`, only `api_token_masked`; `PATCH` of `name` alone keeps the stored token; blank `api_token` on update keeps it; unauthenticated → 401
- [X] T031 [P] [US1] `backend/apps/companies/tests/test_delete_guard.py`: deleting a company referenced by a document → `409 { "code": "company_has_documents" }` (uses the document factory from T057; see Dependencies note)

### Implementation for User Story 1

- [X] T032 [US1] `backend/apps/companies/models.py` — `Company(UUIDModel, TimeStampedModel)` with `name`, `api_token` (write-side `SecretString`), `masked_token` property, `clean()` name validation, `__str__`; `backend/apps/companies/querysets.py` — `CompanyQuerySet.with_document_count()`
- [X] T033 [US1] `backend/apps/companies/migrations/0001_initial.py` (generated, reviewed: UUID PK, indexes)
- [X] T034 [US1] `backend/apps/companies/serializers.py` — `CompanySerializer` with `api_token` write-only + required on create, optional on update (omitted/blank preserves the stored value), `api_token_masked` read-only
- [X] T035 [US1] `backend/apps/companies/views.py` + `backend/apps/companies/urls.py` — thin `CompanyViewSet(ModelViewSet)`; `ProtectedError` surfaces as `409` through the T016 handler; register the router under `/api/companies/` in `backend/config/urls.py`
- [X] T036 [P] [US1] `backend/apps/companies/tests/factories.py` — `CompanyFactory` (`factory-boy`) used by every downstream app's tests
- [X] T037 [P] [US1] Angular company API service in `frontend/src/app/core/api/company.service.ts` + `frontend/src/app/core/models/company.model.ts`
- [X] T038 [US1] Angular companies feature in `frontend/src/app/companies/`: signal-based list + reactive create/edit form + delete with `409` handling; no full-page reload; route wired in `frontend/src/app/app.routes.ts`
- [X] T039 [P] [US1] `frontend/src/app/companies/companies.component.spec.ts` — Jest: list re-renders after create without reload, form validation, masked token displayed

**Checkpoint**: US1 fully functional and testable independently.

---

## Phase 4: User Story 2 - Documents & signers with automatic ZapSign submission (Priority: P1)

**Goal**: Manager can CRUD documents and signers; on create the document is saved locally first,
then submitted to ZapSign (sandbox), storing `open_id`/`token`/`status`; failures leave a retryable
`failed` state; deleting a document deletes its signers.

**Independent Test**: Create a document with one signer + PDF URL → `201`, retrievable even when the
ZapSign mock errors (`provider_status="failed"`); with the mock succeeding, `open_id`/`token`/`status`
populated; `resync` moves `failed`→`submitted`; deleting the document empties its signers.

### Tests for User Story 2 ⚠️ (write first, must fail) — TDD-critical per constitution

- [X] T040 [P] [US2] `backend/apps/integrations/zapsign/tests/test_http_gateway.py` (respx): POST shape + auth position; 200 → `ZapSignCreateResult`; read-timeout → `ZapSignError(kind="timeout")`; 401 → `kind="auth"`; 500 → `kind="http_status"`; malformed body → `kind="invalid_response"`; `api_token` never in logs/exception text — per [contracts/zapsign-gateway.md](./contracts/zapsign-gateway.md)
- [X] T041 [P] [US2] `backend/apps/documents/tests/test_model_rules.py`: `ProviderStatus` `TextChoices` values and the pure transition guard; `Document.can_resync()` (True for `failed`/`submitted`, False for `pending_integration`); `Document.mark_submitted(result)` / `mark_provider_failed(reason)` set fields without saving side effects
- [X] T042 [P] [US2] `backend/apps/documents/tests/test_service_create.py` (`FakeZapSignGateway`): document + signers exist in the DB **before** the gateway call (fake asserts the row at call time); success maps `open_id`/`token`/`status` + `provider_status="submitted"`; `ZapSignError` → `failed` + `last_provider_error`, document retained; local write is one transaction
- [X] T043 [P] [US2] `backend/apps/documents/tests/test_api_documents.py`: `POST /api/documents/` 201 with nested signers; empty `signers` → 400; unknown `company` → 400; `PATCH` name/pdf_url/signers; `DELETE` → 204 then signers gone; `POST /api/documents/{id}/resync/` 200, and `409 resync_not_allowed` when the status forbids it
- [X] T044 [P] [US2] `backend/apps/signers/tests/test_api_signers.py`: standalone CRUD on `/api/signers/`; `?document=` filter; duplicate email on the same document → `400` with `fields.email`; the same email on a different document is allowed
- [X] T045 [P] [US2] `backend/tests/integration/test_zapsign_resilience.py`: ZapSign mock failing during create → 201, document present with `provider_status="failed"`; `resync` with the mock now succeeding → `submitted` (SC-002)

### Implementation for User Story 2

- [X] T046 [P] [US2] `backend/apps/integrations/zapsign/gateway.py` — `ZapSignGateway` ABC + frozen typed `ZapSignSignerInput`/`ZapSignCreateRequest`/`ZapSignSignerResult`/`ZapSignCreateResult`/`ZapSignDocumentStatus`; `ZapSignError` with typed `kind`/`status_code`/`message`
- [X] T047 [US2] `backend/apps/integrations/zapsign/client.py` — `HttpZapSignGateway` (`httpx`, timeouts from `integrations/config.py`, `@log_gateway_call`, `api_token` redaction, full error mapping)
- [X] T048 [P] [US2] `backend/apps/integrations/zapsign/fakes.py` — `FakeZapSignGateway` (queue a success result or a `ZapSignError`, record the last `ZapSignCreateRequest`)
- [X] T049 [US2] `backend/apps/integrations/providers.py` — typed factory functions returning the real or fake gateway per settings (`ZAPSIGN_USE_FAKE`), the single place views/services resolve a provider from
- [X] T050 [P] [US2] `backend/apps/documents/status.py` — `ProviderStatus(TextChoices)` and pure `can_transition()` / `next_status_for()` helpers (no Django model import)
- [X] T051 [US2] `backend/apps/documents/models.py` — `Document(UUIDModel, TimeStampedModel)` (FK `company` `on_delete=PROTECT`, `name`, `pdf_url`, `provider_status`, `open_id`, `token`, `external_id`, `status`, `created_by`, `last_provider_error`, indexes) with `can_resync()`, `mark_submitted()`, `mark_provider_failed()`, `clean()`; `backend/apps/documents/querysets.py` — `DocumentQuerySet` (`for_company`, `by_provider_status`, `with_signers`); migration `0001_initial.py`
- [X] T052 [US2] `backend/apps/signers/models.py` — `Signer(UUIDModel)` (FK `document` `on_delete=CASCADE`, `name`, `email`, `token`, `status`, `external_id`, `UniqueConstraint(document, email)`, `normalized_email` property, `clean()`); `backend/apps/signers/querysets.py` — `SignerQuerySet.for_document()`; migration `0001_initial.py`
- [X] T053 [US2] `backend/apps/documents/services.py` — plain typed functions `create_document(*, data, gateway: ZapSignGateway) -> Document` (atomic local write of Document `pending_integration` + Signers, **then** the gateway call, then map result/`ZapSignError`) and `resync_document(*, document, gateway) -> Document` (guarded by `can_resync()`, raises the `resync_not_allowed` conflict otherwise)
- [X] T054 [US2] `backend/apps/documents/serializers.py` — `DocumentSerializer` (nested writable `signers`, read-only `provider_status`/`status`/`open_id`/`token`/`last_provider_error`) + create validation requiring ≥1 signer and rejecting duplicate emails in the payload
- [X] T055 [US2] `backend/apps/documents/views.py` + `backend/apps/documents/urls.py` — `DocumentViewSet` delegating create/resync to T053 with the gateway injected from T049; `resync` detail action; register `/api/documents/`
- [X] T056 [P] [US2] `backend/apps/signers/serializers.py` + `views.py` + `urls.py` — `SignerViewSet` with `?document=` filtering and the unique-constraint violation surfaced as `fields.email`; register `/api/signers/`
- [X] T057 [P] [US2] `backend/apps/documents/tests/factories.py` + `backend/apps/signers/tests/factories.py` — `DocumentFactory`, `SignerFactory` (unblocks T031)
- [X] T058 [P] [US2] Angular document/signer API services and models in `frontend/src/app/core/api/document.service.ts`, `frontend/src/app/core/api/signer.service.ts`, `frontend/src/app/core/models/document.model.ts`, `frontend/src/app/core/models/signer.model.ts`
- [X] T059 [US2] Angular documents feature in `frontend/src/app/documents/`: signal-based list with status badges, reactive create form with repeatable signer rows + PDF URL, detail view showing provider fields, "Resync" action; no full-page reload
- [X] T060 [P] [US2] Angular inline signer management inside the document form/detail in `frontend/src/app/signers/`
- [X] T061 [P] [US2] `frontend/src/app/documents/documents.component.spec.ts` — Jest: list updates after create/delete, form requires ≥1 signer, resync button shown only for `failed`/`submitted`
- [X] T062 [P] [US2] `frontend/src/app/signers/signer-rows.component.spec.ts` — Jest: add/remove signer rows, duplicate-email error rendered from the API `fields.email`

**Checkpoint**: US1 + US2 both work independently. This is the demoable MVP.

---

## Phase 5: User Story 3 - Automatic AI content analysis (Priority: P2)

**Goal**: On document save (and on demand) the system extracts PDF text, runs the LLM + regex clause
pipeline, and stores an append-only `DocumentAnalysis` (summary, missing topics, insights, source);
failures never affect the document or its ZapSign state; the latest analysis is shown by default and
the full history is available.

**Independent Test**: Save a document with a readable PDF → `latest_analysis.state="succeeded"` with
summary/topics/insights; call `analyze` again → history grows by exactly 1 and the earlier row is
unchanged; an unreachable/image-only PDF → `state="failed"` with `error_reason`, document intact.

### Tests for User Story 3 ⚠️ (write first, must fail) — TDD-critical per constitution

- [X] T063 [P] [US3] `backend/apps/integrations/pdf/tests/test_extractor.py`: `PypdfTextExtractor` with mocked fetch — text extracted; unreachable → `PdfExtractionError(kind="unreachable")`; non-PDF → `not_pdf`; oversize → `too_large`; whitespace-only → `no_text`; timeout → `timeout`
- [X] T064 [P] [US3] `backend/apps/integrations/analysis/tests/test_openai_provider.py` (SDK/HTTP mocked): well-formed JSON → `ProviderAnalysis`; malformed/missing keys → `AnalysisProviderError(kind="invalid_response")`; timeout → `kind="timeout"`; 401 → `kind="auth"`; the API key never appears in logs or exception text
- [X] T065 [P] [US3] `backend/apps/integrations/analysis/tests/test_clause_checker.py`: absent pt-BR clauses reported by label; present clauses (keyword/regex) not reported; the clause set is config-overridable
- [X] T066 [P] [US3] `backend/apps/integrations/analysis/tests/test_pipeline.py`: every branch in [contracts/analysis-provider.md](./contracts/analysis-provider.md) — extractor `no_text` → failed with no provider call; provider success + checker adds `foro` → `source="llm+regex"`, deduped; provider timeout + fallback on → `state="succeeded"`, `source="regex"`; fallback off → `state="failed"`, `error_reason="provider_timeout"`; risk insights preserved
- [X] T067 [P] [US3] `backend/apps/documents/tests/test_service_analyze.py` (fake pipeline + real DB): creates exactly one new `DocumentAnalysis`; a pre-existing row is untouched; a `failed` result still inserts `state="failed"` and does not change `Document.provider_status` (FR-020)
- [X] T068 [P] [US3] `backend/apps/documents/tests/test_api_analyze.py`: `POST /api/documents/{id}/analyze/` → 201 new analysis; `GET /api/documents/{id}/analyses/` paginated newest-first history; `latest_analysis` embedded on the document detail; 404 when the document is gone
- [X] T069 [P] [US3] `backend/tests/integration/test_analysis_resilience.py`: an unreachable `pdf_url` on `POST /api/documents/` still returns 201 with `latest_analysis.state="failed"` and ZapSign fields untouched (SC-010)

### Implementation for User Story 3

- [X] T070 [P] [US3] `backend/apps/integrations/pdf/extractor.py` — `PdfTextExtractor` ABC + `PypdfTextExtractor` (bounded fetch, `PDF_MAX_BYTES` guard, `pypdf`) + `PdfExtractionError`; `backend/apps/integrations/pdf/fakes.py` — `FakePdfTextExtractor`
- [X] T071 [P] [US3] `backend/apps/integrations/analysis/provider.py` — `AnalysisProvider` ABC, frozen `ProviderAnalysis`, `AnalysisProviderError`; `backend/apps/integrations/analysis/results.py` — frozen `AnalysisResult` + `Insight` and the `AnalysisState`/`AnalysisSource` literals the pipeline returns (the persistence-side `TextChoices` land in T075)
- [X] T072 [US3] `backend/apps/integrations/analysis/openai_provider.py` — `OpenAIAnalysisProvider` (direct `openai` SDK, pt-BR structured-JSON prompt, `response_format`, `AI_TIMEOUT_SECONDS`, `AI_MAX_INPUT_CHARS` truncation, `@log_gateway_call`, key redaction, response-shape validation); `backend/apps/integrations/analysis/fakes.py` — `FakeAnalysisProvider`
- [X] T073 [P] [US3] `backend/apps/integrations/analysis/clause_checker.py` — `ClauseChecker` with the default pt-BR clause set, overridable via `AI_EXPECTED_CLAUSES`
- [X] T074 [US3] `backend/apps/integrations/analysis/pipeline.py` — `AnalysisPipeline.run(pdf_url) -> AnalysisResult` orchestrating extract → provider → regex merge, implementing every rule/branch of the contract; touches no database
- [X] T075 [US3] `backend/apps/documents/models.py` (extend) — `DocumentAnalysis(UUIDModel)` (FK `document` `on_delete=CASCADE`, `state`/`source` `TextChoices`, `summary`, `missing_topics` JSON, `insights` JSON, `error_reason`, `model`, `created_at`, index `(document, -created_at)`, `clean()` enforcing the state/summary/error_reason rules) plus `Document.latest_analysis` property and `Document.has_open_risk`; `backend/apps/documents/querysets.py` (extend) — `with_latest_analysis()`, `with_risk()`; migration `0002_documentanalysis.py`
- [X] T076 [US3] `backend/apps/documents/services.py` (extend) — `analyze_document(*, document, pipeline) -> DocumentAnalysis` (run the pipeline, insert a new row, never update) and a non-fatal call to it at the end of `create_document` after the ZapSign step
- [X] T077 [US3] `backend/apps/documents/serializers.py` (extend) — `DocumentAnalysisSerializer`; read-only `latest_analysis` on `DocumentSerializer` served from the annotated queryset (no N+1)
- [X] T078 [US3] `backend/apps/documents/views.py` + `urls.py` (extend) — `analyze` (POST → 201) and `analyses` (GET, paginated, newest-first) detail actions with the pipeline injected from T049
- [X] T079 [P] [US3] Angular analysis model + service methods in `frontend/src/app/core/models/analysis.model.ts` and `frontend/src/app/core/api/document.service.ts` (`analyze`, `analyses`)
- [X] T080 [US3] Angular analysis panel in `frontend/src/app/documents/`: latest analysis (summary, missing topics, insights with risk flag), "Re-analyze" button, history list, failed-state reason
- [X] T081 [P] [US3] `frontend/src/app/documents/analysis-panel.component.spec.ts` — Jest: renders succeeded vs failed analysis, re-analyze triggers the service call, history count updates without reload

**Checkpoint**: US1 + US2 + US3 all independently functional.

---

## Phase 6: User Story 4 - Authenticated programmatic access & reports (Priority: P2)

**Goal**: External automation, with a revocable API key, can create documents, trigger analyses, and
pull per-document and aggregated reports via `/api/automation/**`; every exposed endpoint rejects
missing/invalid/revoked credentials with no data; the ZapSign `api_token` is never exposed.

**Independent Test**: With a valid key, exercise all four automation calls successfully; repeat each
with no key / a JWT / a revoked key and confirm rejection with no body data; the per-document report
contains status + latest analysis; the summary groups by status and lists recent risk insights.

### Tests for User Story 4 ⚠️ (write first, must fail)

- [X] T082 [P] [US4] `backend/apps/documents/tests/test_reports.py`: `document_report()` (signature status + `provider_status` + latest analysis) and `summary_report()` (counts by `provider_status` and signature status, `documents_with_risk_insight`, `recent_risk_insights`); empty dataset → well-formed zeros/empty arrays
- [X] T083 [P] [US4] `backend/apps/automation/tests/test_automation_endpoints.py`: `POST /api/automation/documents/`, `POST /api/automation/documents/{id}/analyze/`, `GET /api/automation/documents/{id}/report/`, `GET /api/automation/reports/summary/` succeed with a valid key; 401 with none/JWT/malformed; 403 with a revoked key; no `api_token` in any response
- [X] T084 [P] [US4] `backend/tests/integration/test_automation_flow.py`: key-only end-to-end — create → analyze → per-document report → the summary reflects the new document (SC-007)
- [X] T085 [P] [US4] `backend/apps/documents/tests/test_api_reports_shared.py`: `GET /api/documents/{id}/report/` and `GET /api/reports/summary/` accept a JWT **and** an API key

### Implementation for User Story 4

- [X] T086 [US4] `backend/apps/documents/reports.py` — typed `document_report(document)` and `summary_report()` built on `DocumentQuerySet` aggregation (no materialised store), per [research.md](./research.md) §15
- [X] T087 [P] [US4] `backend/apps/documents/serializers.py` (extend) — `DocumentReportSerializer`, `SummaryReportSerializer` matching [contracts/openapi.yaml](./contracts/openapi.yaml)
- [X] T088 [US4] `backend/apps/documents/views.py` + `urls.py` (extend) — `report` detail action and `ReportSummaryView` at `/api/reports/summary/`, both permitting `IsAuthenticated` OR `HasApiKey`
- [X] T089 [US4] `backend/apps/automation/views.py` + `backend/apps/automation/urls.py` — thin views delegating to the document services and `reports.py`, with `authentication_classes = [ApiKeyAuthentication]` and `permission_classes = [HasApiKey]`; register `/api/automation/**` in `backend/config/urls.py`
- [X] T090 [P] [US4] `backend/apps/automation/tests/test_no_token_leak.py`: assert `api_token` and `api_token_masked` are absent from every automation response body (FR-002)
- [X] T091 [P] [US4] Angular reports view in `frontend/src/app/reports/` + `frontend/src/app/core/api/report.service.ts` — aggregated summary display consuming `GET /api/reports/summary/`

**Checkpoint**: US1–US4 independently functional; the full API surface is complete.

---

## Phase 7: User Story 5 - Alerts dashboard (Priority: P3, bonus)

**Goal**: A dashboard lists documents pending longer than `ALERT_STALLED_DAYS` and documents whose
latest analysis carries a risk insight; an empty result renders an empty state, not an error.

**Independent Test**: Back-date a document or lower the threshold so it appears as a `stalled` alert;
a document with a `risk=true` insight appears as a `risk` alert; with neither, the endpoint returns
an empty list with 200.

### Tests for User Story 5 ⚠️ (write first, must fail)

- [X] T092 [P] [US5] `backend/apps/documents/tests/test_alerts.py`: `DocumentQuerySet.stalled(threshold)` (non-terminal signature status and `now - created_at > ALERT_STALLED_DAYS`) and `.with_open_risk()`; the alert builder's `{type, document_id, document_name, detail, since}` shape and ordering by `since`; empty → `[]`
- [X] T093 [P] [US5] `backend/apps/documents/tests/test_api_alerts.py`: `GET /api/alerts/` returns the typed items, requires auth, and returns `200` with `[]` when nothing matches (US5 AS-3)

### Implementation for User Story 5

- [X] T094 [P] [US5] `backend/apps/documents/querysets.py` (extend) — `stalled(threshold)` and `with_open_risk()`; `backend/apps/documents/alerts.py` — typed `build_alerts()` composing both into stalled + risk alert items
- [X] T095 [US5] `backend/apps/documents/serializers.py` + `views.py` + `urls.py` (extend) — `AlertSerializer` + `AlertListView` at `/api/alerts/`
- [X] T096 [P] [US5] Angular alerts dashboard in `frontend/src/app/alerts/` + `frontend/src/app/core/api/alert.service.ts`: grouped stalled/risk lists, empty state, route wired
- [X] T097 [P] [US5] `frontend/src/app/alerts/alerts.component.spec.ts` — Jest: both alert groups render; the empty state shows when the list is empty

**Checkpoint**: US1–US5 functional; the bonus oversight surface is added.

---

## Phase 8: User Story 6 - Outbound automation webhook (Priority: P3, bonus)

**Goal**: On a document status change or a risk-bearing analysis, POST a contract-shaped event to
`N8N_WEBHOOK_URL` (best-effort, after commit); delivery failure never affects the document
operation. Ship an example n8n workflow + screenshot.

**Independent Test**: Point `N8N_WEBHOOK_URL` at a receiver, cause a status change / risk analysis,
and verify the payload matches [contracts/webhook-outbound.md](./contracts/webhook-outbound.md);
point it at an unreachable host and confirm `POST /api/documents/` and `.../analyze/` still succeed.

### Tests for User Story 6 ⚠️ (write first, must fail)

- [X] T098 [P] [US6] `backend/apps/automation/tests/test_webhook_notifier.py` (respx): `HttpWebhookNotifier.notify` POSTs the documented JSON once; connection error / timeout / 500 are swallowed (returns `None`); `X-Signature` is a correct HMAC-SHA256 when `N8N_WEBHOOK_SECRET` is set; `NullWebhookNotifier` is selected when the URL is unset and attempts no HTTP
- [X] T099 [P] [US6] `backend/apps/documents/tests/test_service_emits_events.py` (`FakeWebhookNotifier`): a signature-status change emits exactly one `document.status_changed`; a `succeeded` analysis with a risk insight emits one `document.analyzed` with `has_risk_insight=true`; a notifier that raises still does not fail `POST /api/documents/` (FR-032)

### Implementation for User Story 6

- [X] T100 [P] [US6] `backend/apps/automation/webhook.py` — `WebhookNotifier` ABC + `HttpWebhookNotifier` (`httpx`, `WEBHOOK_TIMEOUT_SECONDS`, HMAC signing, `@log_gateway_call`, swallow-all) + `NullWebhookNotifier` + `FakeWebhookNotifier`, and the event builders producing the contract payload
- [X] T101 [US6] `backend/apps/documents/services.py` (extend) — emit `document.status_changed` (from `create_document`/`resync_document` when `status` actually changed) and `document.analyzed` (from `analyze_document`, gated by `WEBHOOK_ON_EVERY_ANALYSIS` when no risk insight) via `transaction.on_commit`, guarded so a notifier failure cannot roll anything back
- [X] T102 [P] [US6] `backend/apps/integrations/providers.py` (extend) — notifier selection (http / null / fake) from `N8N_WEBHOOK_URL` and settings
- [X] T103 [P] [US6] `deploy/n8n/document-events.workflow.json` (exported example: Webhook → IF risk → HTTP Request report → notify) + `deploy/n8n/README.md` + `deploy/n8n/screenshot.png`

**Checkpoint**: All six user stories functional.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Deployment assets, docs, and quality gates spanning all stories.

- [X] T104 [P] Kubernetes base in `deploy/k8s/base/`: `namespace.yaml`, `backend-deployment.yaml` + `backend-service.yaml` (liveness/readiness probes → `/api/health/`, resource requests/limits, non-root), `frontend-deployment.yaml` + `frontend-service.yaml`, `postgres-statefulset.yaml`, `migrate-job.yaml`, `configmap.yaml`, `secret.example.yaml`, `ingress.yaml`, `kustomization.yaml`
- [X] T105 [P] Kustomize overlays `deploy/k8s/overlays/local/` and `deploy/k8s/overlays/prod/` (image tags, replica counts, resource patches, HPA/PDB)
- [X] T106 [P] `README.md`: setup (`docker compose up`), running the tests, endpoint documentation (linking [contracts/rest-api.md](./contracts/rest-api.md) / [openapi.yaml](./contracts/openapi.yaml)), the AI pipeline explanation, and the architecture rationale — Django-idiomatic layering, SOLID at the integration seams, KISS/UUID choices, and the **synchronous-AI trade-off + evolution path** (Constitution Principle III requirement)
- [X] T107 [P] Wire `drf-spectacular` in `backend/config/settings/base.py` + `backend/config/urls.py` to serve `/api/schema/` and `/api/docs/`, and diff the generated schema against `contracts/openapi.yaml`
- [X] T108 [P] `backend/apps/core/management/commands/seed_demo.py` — optional demo `Company` + sample document for the quickstart flow
- [X] T109 Verify the coverage gate: `pytest --cov --cov-fail-under=80` green across the primary-flow packages (`companies`, `documents`, `signers`, `integrations`, `automation`); adjust the `coverage` scope in `backend/pyproject.toml` if needed (SC-009)
- [X] T110 Run `ruff check . && ruff format --check . && mypy .` clean across `backend/`; close every type/lint gap (no blanket `# type: ignore`)
- [X] T111 [P] Frontend: `npm run lint && npm test -- --coverage` green in `frontend/`; close gaps
- [ ] T112 ⚠️ **PARTIAL — sections 1–4 and 6 verified against the running Compose stack; section 5 (`kubectl apply -k`) NOT executed — no Kubernetes cluster is running (Docker Desktop's Kubernetes is disabled). The manifests were validated statically instead: both overlays render, and probes/images/security context/ingress routing/Job policy were asserted against the rendered YAML.** Execute [quickstart.md](./quickstart.md) end-to-end (all six user-story blocks + both test suites + `kubectl apply -k deploy/k8s/overlays/local`) and record the results in the README "Validation" section
- [X] T113 [P] Review structured logging emitted by `backend/apps/core/logging.py` and `backend/apps/core/middleware.py`: exactly one JSON entry per external-dependency call and per primary route with status + `elapsed_ms`, and confirm `api_token`, API keys and the OpenAI key never appear in any log line (Constitution Principle V, FR-029)
- [X] T114 [P] Reconcile the design docs with the implemented architecture: update [data-model.md](./data-model.md) ("Domain dataclass" lines) and [contracts/analysis-provider.md](./contracts/analysis-provider.md) (`documents/domain/entities.py` paths) to the models-as-domain layout, and add the "Architecture Stance" section that [plan.md](./plan.md)'s Principle I row references (including its Project Structure tree, which still shows per-app `domain/` packages)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies — **already complete**.
- **Foundational (Phase 2)**: depends on Setup. **BLOCKS all user stories.**
- **User Stories (Phases 3–8)**: each depends on Foundational.
  - US1 and US2 (both P1) form the MVP.
  - US3 depends on US2 (`Document`, the document services, documents views/serializers).
  - US4 depends on US2 and US3 (`latest_analysis`, `analyze`, risk counts in the summary).
  - US5 depends on US2 and US3 (document age + analysis risk).
  - US6 depends on US2 and US3 (status changes + analysis events).
- **Polish (Phase 9)**: after the targeted stories. T104–T105 are already done; T106–T108 can start
  once the relevant surface exists; T109–T113 are the release gate; T114 can run any time.

### Known cross-story ordering note

T031 (US1 delete guard) asserts a `409` for a company that has a document, so it needs the
`Document` model and `DocumentFactory` from T051/T057 in US2. Write T031 in the US1 phase, but
expect it to go green only after T051/T057 — or temporarily assert the `ProtectedError` mapping in
T016 with a stub FK and revisit T031 after US2.

### User Story Dependencies

| Story | Depends on | Notes |
|-------|-----------|-------|
| US1 (P1) | Foundational | independent (except the T031 note above) |
| US2 (P1) | Foundational | needs only a `Company` row, not the US1 SPA flow |
| US3 (P2) | Foundational, US2 | analysis attaches to documents |
| US4 (P2) | Foundational, US2, US3 | automation reuses the document services and reports |
| US5 (P3) | Foundational, US2, US3 | alerts derive from document age + analysis risk |
| US6 (P3) | Foundational, US2, US3 | events fire on status change + analysis |

### Within Each User Story

- Tests first and failing → `TextChoices`/pure status helpers → models + querysets + migrations →
  services (only where an external call is involved) → serializers → views/urls → Angular service →
  Angular feature → Angular spec.
- Gateway ABCs and their fakes land before any service that consumes them.

### Parallel Opportunities

- Setup: T003–T011 were all `[P]` (complete).
- Foundational: T014–T017, T019, T023, T025–T027 are `[P]` once T012–T013 land.
- Within a story, all `[P]` test files can be written together; backend service work and the
  matching Angular feature can proceed in parallel once the serializer shape is fixed.
- Cross-team: after Foundational, US1 and US2 can be built by different developers; US3–US6
  serialize behind US2, but US5 and US6 are independent of each other.

---

## Parallel Example: User Story 2

```bash
# Write these test files together first (all must fail):
Task: "T040 respx gateway tests in backend/apps/integrations/zapsign/tests/test_http_gateway.py"
Task: "T041 model status-rule tests in backend/apps/documents/tests/test_model_rules.py"
Task: "T042 create-service tests in backend/apps/documents/tests/test_service_create.py"
Task: "T043 documents API tests in backend/apps/documents/tests/test_api_documents.py"
Task: "T044 signers API tests in backend/apps/signers/tests/test_api_signers.py"

# Then the independent implementation units in parallel:
Task: "T046 ZapSign gateway ABC + typed DTOs"
Task: "T048 FakeZapSignGateway"
Task: "T050 ProviderStatus TextChoices + pure transition helpers"
```

---

## Implementation Strategy

### MVP First

1. Phase 1 Setup (done) → Phase 2 Foundational.
2. Phase 3 (US1) → **validate**: organization profile CRUD with a masked credential.
3. Phase 4 (US2) → **validate**: document/signer CRUD + ZapSign submission + `failed`/`resync` +
   cascade delete. This is the demoable MVP.
4. Stop / demo.

### Incremental Delivery

- + US3: automatic AI insights on every document → demo.
- + US4: authenticated automation API + reports → demo (n8n can now integrate).
- + US5: alerts dashboard → demo (bonus).
- + US6: outbound webhook + example n8n workflow → demo (bonus).
- Phase 9 polish folds in progressively; T109–T113 are the release gate.

### Test discipline (constitution Principle II)

- For every task in a "Tests for User Story N" block: write it, run it, confirm it **fails**, then
  implement. ZapSign, OpenAI and the webhook receiver are always mocked — the suite makes no
  external network calls, locally or in CI.

---

## Notes

- `[P]` = different files, no dependency on an incomplete task.
- `[Story]` labels (US1–US6) map each task to a spec.md user story for traceability.
- Commit after each task or logical group; stop at any checkpoint to validate a story independently.
- `api_token` (ZapSign) is write-only everywhere and absent from every `automation` response —
  enforced by T034, T083, T090, T113.
- `DocumentAnalysis` is append-only: no task adds an update or overwrite path (FR-017).
- Task IDs T012, T015, T021 and T106 are referenced from comments in `backend/config/`; keep their
  meaning stable if this file is regenerated.
