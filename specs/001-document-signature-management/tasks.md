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

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project skeleton, tooling, container and CI scaffolding.

- [X] T001 Create monorepo directory structure (`backend/`, `frontend/`, `deploy/`, `.github/workflows/`, `README.md` stub) per [plan.md](./plan.md) "Source Code" tree
- [ ] T002 Initialize Django project in `backend/`: `backend/pyproject.toml` (Django 5.x LTS, DRF, `djangorestframework-simplejwt`, `djangorestframework-api-key`, `openai`, `pypdf`, `httpx`, `psycopg[binary]`, `python-json-logger`), `backend/manage.py`, `backend/config/{__init__,urls,wsgi,asgi}.py`, `backend/config/settings/{base,local,prod}.py`
- [ ] T003 [P] Configure backend tooling in `backend/pyproject.toml`: `ruff` (lint+format), `mypy` + `django-stubs` + `djangorestframework-stubs` (pragmatic-strict per [research.md](./research.md) §9), `pytest`/`pytest-django`/`pytest-cov`/`factory-boy`/`respx` with `--cov-fail-under=80` on primary-flow packages
- [ ] T004 [P] Initialize Angular 19 app in `frontend/` (standalone components, routing) with Jest via `jest-preset-angular`: `frontend/package.json`, `frontend/jest.config.ts`, `frontend/src/test/setup.ts`, ESLint config
- [X] T005 [P] Create `backend/Dockerfile` (multi-stage, non-root, `gunicorn` runtime, k8s-ready) per [research.md](./research.md) §12
- [ ] T006 [P] Create `frontend/Dockerfile` (multi-stage build → nginx static runtime) + `frontend/nginx.conf`
- [X] T007 [P] Create `deploy/.env.example` documenting every variable (`POSTGRES_*`, `DJANGO_SECRET_KEY`, `DJANGO_SETTINGS_MODULE`, `ZAPSIGN_BASE_URL`, `ZAPSIGN_TIMEOUT_SECONDS`, `OPENAI_API_KEY`, `AI_MODEL`, `AI_TIMEOUT_SECONDS`, `AI_MAX_INPUT_CHARS`, `AI_REGEX_FALLBACK_ENABLED`, `PDF_FETCH_TIMEOUT_SECONDS`, `PDF_MAX_BYTES`, `ALERT_STALLED_DAYS`, `N8N_WEBHOOK_URL`, `N8N_WEBHOOK_SECRET`, `WEBHOOK_TIMEOUT_SECONDS`, `PUBLIC_BASE_URL`)
- [X] T008 [P] Create `deploy/docker-compose.yml` with services `db` (postgres:16), `migrate` (one-shot), `backend` (:8000), `frontend` (:4200), healthchecks and `.env` wiring
- [X] T009 [P] Create `.github/workflows/backend.yml`: setup Python 3.12 → install → `ruff check` + `ruff format --check` → `mypy` → `pytest --cov --cov-fail-under=80` against a `postgres:16` service; no third-party network
- [X] T010 [P] Create `.github/workflows/frontend.yml`: setup Node 20 → `npm ci` → `eslint` → `jest --coverage` → `npm run build`
- [X] T011 [P] Create `.github/workflows/images.yml`: Buildx build of backend + frontend images with layer cache; push to GHCR only on default branch / tags

**Checkpoint**: `docker compose -f deploy/docker-compose.yml config` validates; empty test suites run.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Cross-cutting infrastructure every user story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T012 Configure `backend/config/settings/base.py` from env (typed helpers): `DATABASES` (PostgreSQL), `INSTALLED_APPS` (DRF, `rest_framework_simplejwt`, `rest_framework_api_key`, the 6 local apps), `REST_FRAMEWORK` (default auth = JWT, default permission = IsAuthenticated, pagination), `AUTH_USER_MODEL` default, timezone UTC
- [ ] T013 Create `backend/apps/core/` app: `apps.py`, `domain/__init__.py`, `domain/enums.py` (shared base enums), `domain/types.py` (`SecretString` value object with masking)
- [ ] T014 [P] Implement structured logging in `backend/apps/core/logging.py`: `python-json-logger` formatter, `log_gateway_call` decorator (provider, operation, outcome, `elapsed_ms`, redaction hook) per [research.md](./research.md) §10
- [ ] T015 [P] Implement `backend/apps/core/middleware.py` `RequestTimingLogger` (method, path, status, `elapsed_ms`, correlation id) and register it in settings
- [ ] T016 [P] Implement DRF exception handler in `backend/apps/core/exceptions.py` producing the standard error body `{detail, code, fields}` from [contracts/rest-api.md](./contracts/rest-api.md); wire `EXCEPTION_HANDLER` in settings
- [ ] T017 [P] Implement `backend/apps/core/pagination.py` `DefaultPageNumberPagination` (`page`, `page_size` 1–100, default 20)
- [ ] T018 Implement health check in `backend/apps/core/health.py` + `backend/apps/core/urls.py`: `GET /api/health/` unauthenticated, DB check → 200/503, best-effort time-boxed `zapsign`/`openai` reachability checks that never fail the endpoint (FR-027, [research.md](./research.md) §11)
- [ ] T019 [P] `backend/apps/core/tests/test_health.py`: 200 when DB ok; 503 when DB check raises; provider check failure keeps 200; endpoint requires no auth
- [ ] T020 Implement typed integration settings in `backend/apps/integrations/__init__.py` + `backend/apps/integrations/config.py` (dataclass reading `ZAPSIGN_*`, `AI_*`, `PDF_*`, `WEBHOOK_*`, `N8N_*` with defaults from the contracts)
- [ ] T021 Wire root URLconf `backend/config/urls.py`: mount `/api/health/`, `/api/auth/`, and per-app routers under `/api/`
- [ ] T022 Implement JWT auth endpoints (`POST /api/auth/token/`, `/api/auth/token/refresh/`) via `simplejwt` in `backend/config/urls.py` + settings; error body maps to `invalid_credentials`
- [ ] T023 [P] Create `backend/apps/core/management/commands/seed_user.py` to create the internal manager user (idempotent, credentials from env)
- [ ] T024 Create `backend/apps/automation/` app with `auth.py`: API-key authentication class (`Authorization: Api-Key <key>`) + `HasApiKey` permission that rejects missing/malformed/revoked/expired keys with no body data (FR-023); JWT is not accepted on this class
- [ ] T025 [P] Create `backend/apps/automation/management/commands/{create_api_key,revoke_api_key}.py` (print plaintext once on create; revoke by prefix)
- [ ] T026 [P] `backend/apps/automation/tests/test_api_key_auth.py`: valid key passes; missing/malformed/revoked/expired → 401/403 with empty data; a JWT is rejected by the API-key permission
- [ ] T027 [P] Scaffold Angular core in `frontend/src/app/core/`: `api/http.service.ts` (base URL, error mapping), `auth/auth.interceptor.ts` (Bearer), `auth/auth.service.ts` + token storage, `auth/login.component.ts`, `models/` (empty index), app routing shell + shared error component in `frontend/src/app/shared/`
- [ ] T028 Verify end-to-end skeleton: `docker compose up` brings `db`+`migrate`+`backend`+`frontend` healthy; `curl /api/health/` returns 200; Angular login page loads

**Checkpoint**: Foundation ready — user stories can now proceed.

---

## Phase 3: User Story 1 - Organization profile & signature credentials (Priority: P1) 🎯 MVP

**Goal**: Manager can create, view, update, and delete the organization profile holding the ZapSign
credential; the credential is never returned in full; deletion is blocked while documents exist.

**Independent Test**: Create a profile with name + `api_token`; confirm it lists with only
`api_token_masked`; edit the name without resending the token; delete it (and, after US2, confirm a
profile with a document returns `409`).

### Tests for User Story 1 ⚠️ (write first, must fail)

- [ ] T029 [P] [US1] `backend/apps/companies/tests/test_domain.py`: `Company` entity rules — `masked_token()`, `with_updated_name()`, non-empty name enforcement
- [ ] T030 [P] [US1] `backend/apps/companies/tests/test_api.py`: CRUD round-trip; response never contains `api_token`, only `api_token_masked`; PATCH name keeps stored token; unauthenticated → 401
- [ ] T031 [P] [US1] `backend/apps/companies/tests/test_delete_guard.py`: deleting a company referenced by a document → `409 company_has_documents` (uses a document factory)

### Implementation for User Story 1

- [ ] T032 [P] [US1] `backend/apps/companies/domain/entities.py` — frozen typed `Company` dataclass; `domain/rules.py` — name validation + deletion guard predicate
- [ ] T033 [US1] `backend/apps/companies/models.py` — `Company` model (UUID PK, `name`, `api_token` via `SecretString`, `created_at`, `last_updated_at`); `backend/apps/companies/migrations/0001_initial.py`
- [ ] T034 [US1] `backend/apps/companies/services.py` — `CompanyService` (create, update-preserving-token, delete-with-guard)
- [ ] T035 [US1] `backend/apps/companies/serializers.py` — `api_token` write-only, `api_token_masked` read-only, optional on update
- [ ] T036 [US1] `backend/apps/companies/views.py` + `urls.py` — DRF `ModelViewSet`; map `ProtectedError` → `409`; register under `/api/companies/`
- [ ] T037 [P] [US1] Angular company API service in `frontend/src/app/core/api/company.service.ts` + `frontend/src/app/core/models/company.model.ts`
- [ ] T038 [US1] Angular companies feature in `frontend/src/app/companies/`: signal-based list + reactive create/edit form + delete with `409` handling; no full-page reload; route wired
- [ ] T039 [P] [US1] `frontend/src/app/companies/companies.component.spec.ts` — Jest: list renders after create, form validation, masked token displayed

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

- [ ] T040 [P] [US2] `backend/apps/integrations/zapsign/tests/test_http_gateway.py` (respx): POST shape + auth position; 200 → `ZapSignCreateResult`; read-timeout → `ZapSignError(kind="timeout")`; 401 → `kind="auth"`; 500 → `kind="http_status"`; malformed body → `kind="invalid_response"`; `api_token` never in logs/exception text — per [contracts/zapsign-gateway.md](./contracts/zapsign-gateway.md)
- [ ] T041 [P] [US2] `backend/apps/documents/tests/test_status_rules.py`: `ProviderStatus` transitions and `can_resync()` (allowed for `failed`/`submitted`, blocked for `pending_integration`)
- [ ] T042 [P] [US2] `backend/apps/documents/tests/test_document_service_create.py` (FakeZapSignGateway): document + signers persisted **before** the gateway call; success maps provider fields + `submitted`; `ZapSignError` → `failed` + `last_provider_error`, document retained; runs in one transaction
- [ ] T043 [P] [US2] `backend/apps/documents/tests/test_api_documents.py`: `POST /api/documents/` 201 with nested signers; empty `signers` → 400; unknown `company` → 400; PATCH name/pdf_url/signers; `DELETE` → 204 then signers gone; `POST /api/documents/{id}/resync/` 200 and `409 resync_not_allowed` when not allowed
- [ ] T044 [P] [US2] `backend/apps/signers/tests/test_api_signers.py`: standalone CRUD; duplicate email on same document → `400` with `fields.email`; same email on different documents allowed
- [ ] T045 [P] [US2] `backend/tests/integration/test_zapsign_resilience.py`: ZapSign mock down during create → 201, document present, `provider_status="failed"`; `resync` with mock now up → `submitted`

### Implementation for User Story 2

- [ ] T046 [P] [US2] `backend/apps/integrations/zapsign/gateway.py` — `ZapSignGateway` ABC + frozen typed `ZapSignCreateRequest`/`ZapSignSignerInput`/`ZapSignCreateResult`/`ZapSignSignerResult`/`ZapSignDocumentStatus`; `ZapSignError` with typed `kind`
- [ ] T047 [US2] `backend/apps/integrations/zapsign/client.py` — `HttpZapSignGateway` (`httpx`, timeouts from `config.py`, `@log_gateway_call`, `api_token` redaction, error mapping)
- [ ] T048 [P] [US2] `backend/apps/integrations/zapsign/fakes.py` — `FakeZapSignGateway` (queue success/error, record last request)
- [ ] T049 [US2] Provider selection in `backend/apps/integrations/__init__.py` (or `providers.py`) — factory returning real or fake gateway based on settings
- [ ] T050 [P] [US2] `backend/apps/documents/domain/status.py` — `ProviderStatus` enum + pure transition functions; `backend/apps/documents/domain/entities.py` — `Document` dataclass (`can_resync`, `mark_submitted`, `mark_provider_failed`)
- [ ] T051 [P] [US2] `backend/apps/signers/domain/entities.py` — `Signer` dataclass + `domain/rules.py` (email/name validation, `normalized_email`)
- [ ] T052 [US2] `backend/apps/documents/models.py` — `Document` model (UUID PK, FK `company` `on_delete=PROTECT`, `pdf_url`, `provider_status`, `open_id`, `token`, `external_id`, `status`, `created_by`, `last_provider_error`, timestamps, indexes); `backend/apps/documents/migrations/0001_initial.py`
- [ ] T053 [US2] `backend/apps/signers/models.py` — `Signer` model (UUID PK, FK `document` `on_delete=CASCADE`, `name`, `email`, `token`, `status`, `external_id`, `UniqueConstraint(document, email)`); `backend/apps/signers/migrations/0001_initial.py`
- [ ] T054 [US2] `backend/apps/documents/services.py` — `DocumentService.create` (atomic: write Document `pending_integration` + Signers → call gateway → map result/`ZapSignError`) and `DocumentService.resync` (guarded)
- [ ] T055 [P] [US2] `backend/apps/signers/services.py` — `SignerService` CRUD with duplicate-email rule surfaced as field error
- [ ] T056 [US2] `backend/apps/documents/serializers.py` — `DocumentSerializer` (nested writable `signers`, read-only provider fields) + `DocumentCreateSerializer` (≥1 signer)
- [ ] T057 [US2] `backend/apps/documents/views.py` + `urls.py` — documents `ModelViewSet` + `resync` action; register `/api/documents/`
- [ ] T058 [P] [US2] `backend/apps/signers/serializers.py` + `views.py` + `urls.py` — signers `ModelViewSet` with `?document=` filter; register `/api/signers/`
- [ ] T059 [P] [US2] Angular document/signer API services + models in `frontend/src/app/core/api/document.service.ts`, `signer.service.ts`, `frontend/src/app/core/models/{document,signer}.model.ts`
- [ ] T060 [US2] Angular documents feature in `frontend/src/app/documents/`: signal-based list (status badges), reactive create form with repeatable signer rows + PDF URL, detail view showing provider fields, "Resync" action; no reload
- [ ] T061 [P] [US2] Angular signer inline management within document form/detail in `frontend/src/app/signers/`
- [ ] T062 [P] [US2] `frontend/src/app/documents/documents.component.spec.ts` — Jest: list updates after create/delete; form requires ≥1 signer; resync button visible only for `failed`/`submitted`

**Checkpoint**: US1 + US2 both work independently. This is a demoable MVP+1.

---

## Phase 5: User Story 3 - Automatic AI content analysis (Priority: P2)

**Goal**: On document save (and on demand) the system extracts PDF text, runs the LLM + regex
clause pipeline, and stores an append-only `DocumentAnalysis` (summary, missing topics, insights,
source); failures never affect the document or its ZapSign state; latest analysis shown by default,
full history available.

**Independent Test**: Save a document with a readable PDF → `latest_analysis.state="succeeded"` with
summary/topics/insights; call `analyze` again → history grows by 1, earlier row unchanged;
unreachable/image-only PDF → `state="failed"` with `error_reason`, document intact.

### Tests for User Story 3 ⚠️ (write first, must fail) — TDD-critical per constitution

- [ ] T063 [P] [US3] `backend/apps/integrations/pdf/tests/test_extractor.py`: `PypdfTextExtractor` with mocked fetch — text extracted; unreachable → `PdfExtractionError(kind="unreachable")`; non-PDF → `not_pdf`; oversize → `too_large`; whitespace-only → `no_text`; timeout → `timeout`
- [ ] T064 [P] [US3] `backend/apps/integrations/analysis/tests/test_openai_provider.py` (SDK/HTTP mocked): well-formed JSON → `ProviderAnalysis`; malformed/missing keys → `AnalysisProviderError(kind="invalid_response")`; timeout → `kind="timeout"`; 401 → `kind="auth"`; API key never logged
- [ ] T065 [P] [US3] `backend/apps/integrations/analysis/tests/test_clause_checker.py`: absent clauses reported; present clauses (pt-BR keyword/regex) not reported
- [ ] T066 [P] [US3] `backend/apps/integrations/analysis/tests/test_pipeline.py`: all branches from [contracts/analysis-provider.md](./contracts/analysis-provider.md) — extractor `no_text` (no provider call); provider success + checker adds `foro` → `source="llm+regex"`, deduped; provider timeout + fallback on → `state="succeeded"`, `source="regex"`; fallback off → `state="failed"`; risk insight preserved
- [ ] T067 [P] [US3] `backend/apps/documents/tests/test_document_service_analyze.py` (fake pipeline + DB): creates exactly one new `DocumentAnalysis`; pre-existing row untouched; `failed` result still inserts `state="failed"` and does not change `Document.provider_status`
- [ ] T068 [P] [US3] `backend/apps/documents/tests/test_api_analyze.py`: `POST /api/documents/{id}/analyze/` → 201 new analysis; `GET /api/documents/{id}/analyses/` newest-first history; `latest_analysis` embedded on the document; 404 when document gone
- [ ] T069 [P] [US3] `backend/tests/integration/test_analysis_resilience.py`: unreachable `pdf_url` on `POST /api/documents/` → 201, `latest_analysis.state="failed"`, ZapSign fields untouched (SC-010)

### Implementation for User Story 3

- [ ] T070 [P] [US3] `backend/apps/integrations/pdf/extractor.py` — `PdfTextExtractor` ABC + `PypdfTextExtractor` (bounded fetch, size guard, `pypdf`) + `PdfExtractionError`; `pdf/fakes.py` — `FakePdfTextExtractor`
- [ ] T071 [P] [US3] `backend/apps/integrations/analysis/provider.py` — `AnalysisProvider` ABC + `ProviderAnalysis`; `backend/apps/documents/domain/entities.py` (extend) — `AnalysisResult` + `Insight` dataclasses
- [ ] T072 [US3] `backend/apps/integrations/analysis/openai_provider.py` — `OpenAIAnalysisProvider` (direct `openai` SDK, pt-BR structured-JSON prompt, `response_format`, timeout, `@log_gateway_call`, key redaction, shape validation); `analysis/fakes.py` — `FakeAnalysisProvider`
- [ ] T073 [P] [US3] `backend/apps/integrations/analysis/clause_checker.py` — `ClauseChecker` with default pt-BR clause set, config-overridable via `AI_EXPECTED_CLAUSES`
- [ ] T074 [US3] `backend/apps/integrations/analysis/pipeline.py` — `AnalysisPipeline.run(pdf_url)` orchestrating extract → provider → regex merge → `AnalysisResult`, implementing every rule/branch in the contract
- [ ] T075 [US3] `backend/apps/documents/models.py` (extend) — `DocumentAnalysis` model (UUID PK, FK `document` `on_delete=CASCADE`, `state`, `summary`, `missing_topics` JSON, `insights` JSON, `source`, `error_reason`, `model`, `created_at`, index `(document, -created_at)`); migration `0002_documentanalysis.py`
- [ ] T076 [US3] `backend/apps/documents/services.py` (extend) — `DocumentService.analyze(document_id)` (run pipeline → insert new `DocumentAnalysis`, never update); call it once (non-fatal) at the end of `create` after the ZapSign step
- [ ] T077 [US3] `backend/apps/documents/serializers.py` (extend) — `DocumentAnalysisSerializer`; add read-only `latest_analysis` to `DocumentSerializer` (annotated queryset for efficiency)
- [ ] T078 [US3] `backend/apps/documents/views.py` + `urls.py` (extend) — `analyze` (POST→201) and `analyses` (GET history, paginated, newest-first) actions
- [ ] T079 [P] [US3] Angular analysis models + service methods in `frontend/src/app/core/models/analysis.model.ts` and `document.service.ts` (analyze, analyses history)
- [ ] T080 [US3] Angular analysis panel in `frontend/src/app/documents/`: show latest analysis (summary, missing topics, insights with risk flag) on the detail view, "Re-analyze" button, history list
- [ ] T081 [P] [US3] `frontend/src/app/documents/analysis-panel.component.spec.ts` — Jest: renders succeeded vs failed analysis; re-analyze triggers service call; history count updates

**Checkpoint**: US1 + US2 + US3 all independently functional.

---

## Phase 6: User Story 4 - Authenticated programmatic access & reports (Priority: P2)

**Goal**: External automation, with a revocable API key, can create documents, trigger analyses, and
pull per-document and aggregated reports via `/api/automation/**`; every exposed endpoint rejects
missing/invalid/revoked credentials with no data; the ZapSign `api_token` is never exposed.

**Independent Test**: With a valid key, exercise all four automation calls successfully; repeat each
with no key / a JWT / a revoked key and confirm rejection with no body data; per-doc report contains
status + latest analysis; summary groups documents by status and lists recent risk insights.

### Tests for User Story 4 ⚠️ (write first, must fail)

- [ ] T082 [P] [US4] `backend/apps/documents/tests/test_reports.py`: `ReportService.document_report` (status + `provider_status` + latest analysis); `ReportService.summary` (counts by `provider_status` and signature status, `documents_with_risk_insight`, `recent_risk_insights`); empty dataset → well-formed zeros/empty arrays
- [ ] T083 [P] [US4] `backend/apps/automation/tests/test_automation_endpoints.py`: `POST /api/automation/documents/`, `POST /api/automation/documents/{id}/analyze/`, `GET /api/automation/documents/{id}/report/`, `GET /api/automation/reports/summary/` — succeed with a valid key; 401 with none/JWT/malformed; 403 with a revoked key; responses contain no `api_token`
- [ ] T084 [P] [US4] `backend/tests/integration/test_automation_flow.py`: key-only end-to-end — create → analyze → per-doc report → summary reflects the new document
- [ ] T085 [P] [US4] `backend/apps/documents/tests/test_api_reports_shared.py`: `GET /api/documents/{id}/report/` and `GET /api/reports/summary/` accept JWT **and** API key

### Implementation for User Story 4

- [ ] T086 [US4] `backend/apps/documents/services.py` (extend) — `ReportService` with `document_report(id)` and `summary()` using ORM aggregation (no materialized store)
- [ ] T087 [P] [US4] `backend/apps/documents/serializers.py` (extend) — `DocumentReportSerializer`, `SummaryReportSerializer` per [contracts/openapi.yaml](./contracts/openapi.yaml)
- [ ] T088 [US4] `backend/apps/documents/views.py` + `urls.py` (extend) — `report` action on documents; `ReportSummaryView` at `/api/reports/summary/`; both permit `IsAuthenticated` OR `HasApiKey`
- [ ] T089 [US4] `backend/apps/automation/views.py` + `urls.py` — thin views delegating to `DocumentService`/`ReportService`, `authentication_classes = [ApiKeyAuthentication]`, `permission_classes = [HasApiKey]`; register `/api/automation/...`; ensure serializers omit `api_token`/JWT-only fields
- [ ] T090 [P] [US4] `backend/apps/automation/tests/test_no_token_leak.py`: assert `api_token` / `api_token_masked` absent from every automation response body
- [ ] T091 [P] [US4] Angular reports view in `frontend/src/app/reports/` (optional SPA surface): aggregated summary display consuming `GET /api/reports/summary/` + `frontend/src/app/core/api/report.service.ts`

**Checkpoint**: US1–US4 independently functional; full API surface complete.

---

## Phase 7: User Story 5 - Alerts dashboard (Priority: P3, bonus)

**Goal**: A dashboard lists documents pending longer than `ALERT_STALLED_DAYS` and documents whose
latest analysis carries a risk insight; empty result renders an empty state, not an error.

**Independent Test**: Back-date / lower threshold so a pending document appears as a `stalled` alert;
a document with a `risk=true` insight appears as a `risk` alert; with neither, the endpoint returns
an empty list.

### Tests for User Story 5 ⚠️ (write first, must fail)

- [ ] T092 [P] [US5] `backend/apps/documents/tests/test_alerts.py`: `AlertService` — stalled rule (`now - created_at > ALERT_STALLED_DAYS` and non-terminal status); risk rule (`Document.has_open_risk`); empty → `[]`; ordering by `since`
- [ ] T093 [P] [US5] `backend/apps/documents/tests/test_api_alerts.py`: `GET /api/alerts/` returns typed items `{type, document_id, document_name, detail, since}`; requires auth; empty state is `200` with `[]`

### Implementation for User Story 5

- [ ] T094 [P] [US5] `backend/apps/documents/domain/entities.py` (extend) — `has_open_risk` helper; `backend/apps/documents/services.py` (extend) — `AlertService.list()` computing `stalled` + `risk` alerts
- [ ] T095 [US5] `backend/apps/documents/serializers.py` + `views.py` + `urls.py` (extend) — `AlertSerializer` + `AlertListView` at `/api/alerts/`
- [ ] T096 [P] [US5] Angular alerts dashboard in `frontend/src/app/alerts/` + `frontend/src/app/core/api/alert.service.ts`: grouped stalled/risk lists, empty state, route wired
- [ ] T097 [P] [US5] `frontend/src/app/alerts/alerts.component.spec.ts` — Jest: renders both alert groups; empty state shown when list is empty

**Checkpoint**: US1–US5 functional; bonus oversight surface added.

---

## Phase 8: User Story 6 - Outbound automation webhook (Priority: P3, bonus)

**Goal**: On document status change or a risk-bearing analysis, POST a contract-shaped event to
`N8N_WEBHOOK_URL` (best-effort, after commit); delivery failure never affects the document operation.
Ship an example n8n workflow + screenshot.

**Independent Test**: Point `N8N_WEBHOOK_URL` at a receiver, cause a status change / risk analysis,
verify the payload matches [contracts/webhook-outbound.md](./contracts/webhook-outbound.md); point it
at an unreachable host and confirm `POST /api/documents/` and `.../analyze/` still succeed.

### Tests for User Story 6 ⚠️ (write first, must fail)

- [ ] T098 [P] [US6] `backend/apps/automation/tests/test_webhook_notifier.py` (respx): `HttpWebhookNotifier.notify` POSTs the documented JSON once; connection error / timeout / 500 swallowed (returns `None`); `X-Signature` is a correct HMAC-SHA256 when `N8N_WEBHOOK_SECRET` set; `NullWebhookNotifier` used when URL unset
- [ ] T099 [P] [US6] `backend/apps/documents/tests/test_service_emits_events.py` (FakeWebhookNotifier): a signature-status change emits one `document.status_changed`; a `succeeded` analysis with a risk insight emits one `document.analyzed` (`has_risk_insight=true`); a notifier that raises does not fail `POST /api/documents/`

### Implementation for User Story 6

- [ ] T100 [P] [US6] `backend/apps/automation/webhook.py` — `WebhookNotifier` ABC + `HttpWebhookNotifier` (`httpx`, timeout, HMAC, `@log_gateway_call`, swallow-all) + `NullWebhookNotifier` + `FakeWebhookNotifier`; event builders producing the contract payload
- [ ] T101 [US6] `backend/apps/documents/services.py` (extend) — after the surrounding transaction commits, call `WebhookNotifier.notify(...)` on status change (in `create`/`resync`) and on new `DocumentAnalysis` (in `analyze`), guarded so failure cannot roll back
- [ ] T102 [P] [US6] Notifier selection in `backend/apps/integrations/__init__.py` — real vs null vs fake based on `N8N_WEBHOOK_URL`/settings
- [X] T103 [P] [US6] `deploy/n8n/document-events.workflow.json` (exported example: Webhook → IF risk → HTTP Request report → notify) + `deploy/n8n/README.md` describing import + the screenshot placeholder `deploy/n8n/screenshot.png`

**Checkpoint**: All six user stories functional.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Deployment assets, docs, and quality gates spanning all stories.

- [X] T104 [P] Kubernetes base in `deploy/k8s/base/`: `namespace.yaml`, `backend-deployment.yaml` + `backend-service.yaml` (liveness/readiness probes → `/api/health/`, resource requests/limits, non-root), `frontend-deployment.yaml` + `frontend-service.yaml`, `postgres-statefulset.yaml`, `configmap.yaml`, `secret.example.yaml`, `ingress.yaml`, `kustomization.yaml`
- [X] T105 [P] Kustomize overlays `deploy/k8s/overlays/local/` and `deploy/k8s/overlays/prod/` (image tags, replica counts, env differences)
- [ ] T106 [P] `README.md`: setup (`docker compose up`), running tests, endpoint documentation (link [contracts/rest-api.md](./contracts/rest-api.md) / [openapi.yaml](./contracts/openapi.yaml)), the AI pipeline explanation, and the SOLID / DDD-light / KISS / UUID and **synchronous-AI trade-off + evolution path** rationale (Constitution Principle III requirement)
- [ ] T107 [P] Add `drf-spectacular` (or equivalent) to serve `/api/schema/` and verify it matches `contracts/openapi.yaml`; wire in settings + `config/urls.py`
- [ ] T108 [P] `backend/apps/core/management/commands/seed_demo.py` — optional demo Company + sample document for quickstart
- [ ] T109 Verify coverage gate: `pytest --cov --cov-fail-under=80` green on primary-flow packages (companies, documents, signers, integrations, automation); adjust `pyproject.toml` `cov` scope if needed
- [ ] T110 Run `ruff check . && ruff format --check . && mypy .` clean across `backend/`; fix type/lint gaps
- [ ] T111 [P] Frontend: `npm run lint && npm test -- --coverage` green; fix gaps
- [ ] T112 Execute [quickstart.md](./quickstart.md) end-to-end (all six User Story blocks + test suites + `kubectl apply -k deploy/k8s/overlays/local`) and record results in the README "Validation" section
- [ ] T113 [P] Review structured logging: confirm one JSON entry per external-dependency call and per primary route with status + `elapsed_ms`, and that `api_token` / API keys / OpenAI key never appear (Constitution Principle V, FR-029)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: depends on Setup. **BLOCKS all user stories.**
- **User Stories (Phases 3–8)**: each depends only on Foundational.
  - US1, US2 (P1) first for the MVP. US2's test T031/T042/T043 use a document factory but the
    `Document` model lands in US2 itself — US1's delete-guard test T031 depends on T052 (Document
    model) if run literally; keep T031 in US1 but mark it runnable once T052 exists, or stub the FK
    check. Practically: do US1 through T038, then US2, then revisit T031.
  - US3 depends on US2 (needs `Document`, `DocumentService`, documents views/serializers).
  - US4 depends on US2 (documents) and US3 (`latest_analysis`, `analyze` for the automation
    `analyze` endpoint and risk counts in the summary).
  - US5 depends on US3 (risk insight) and US2 (pending documents).
  - US6 depends on US2 (status changes) and US3 (analysis events).
- **Polish (Phase 9)**: after all targeted stories; T104–T105 (k8s) only need a runnable backend +
  frontend image and can start in parallel with US3+.

### User Story Dependencies

| Story | Depends on | Notes |
|-------|-----------|-------|
| US1 (P1) | Foundational | independent |
| US2 (P1) | Foundational | independent of US1 at runtime (documents don't require the SPA company flow, only a `Company` row) |
| US3 (P2) | Foundational, US2 | analysis attaches to documents |
| US4 (P2) | Foundational, US2, US3 | automation reuses document + analysis services; summary counts risk insights |
| US5 (P3) | Foundational, US2, US3 | derives alerts from document age + analysis risk |
| US6 (P3) | Foundational, US2, US3 | emits events on status change + analysis |

### Within Each User Story

- Tests first and failing → domain dataclasses/rules → models + migrations → services → serializers
  → views/urls → Angular service → Angular feature → Angular spec.
- Gateways/interfaces (ABC + fakes) before the services that consume them.

### Parallel Opportunities

- Setup: T003–T011 all `[P]`.
- Foundational: T014–T017, T019, T023, T025–T027 `[P]` after T012–T013.
- Within a story, all `[P]` test files can be written together; domain dataclasses across apps are
  `[P]`; backend service work and the matching Angular feature can proceed in parallel once the
  serializer/contract is fixed.
- Cross-team: after Foundational, US1 and US2 can be built by different developers; US3/US4/US5/US6
  serialize behind US2 but US5 and US6 are independent of each other.

---

## Parallel Example: User Story 2

```bash
# Write these test files together first (all must fail):
Task: "T040 respx gateway tests in backend/apps/integrations/zapsign/tests/test_http_gateway.py"
Task: "T041 status-rule tests in backend/apps/documents/tests/test_status_rules.py"
Task: "T042 DocumentService.create tests in backend/apps/documents/tests/test_document_service_create.py"
Task: "T043 documents API tests in backend/apps/documents/tests/test_api_documents.py"
Task: "T044 signers API tests in backend/apps/signers/tests/test_api_signers.py"

# Then domain dataclasses across apps in parallel:
Task: "T050 documents domain status + entities"
Task: "T051 signers domain entities + rules"
Task: "T046 ZapSign gateway ABC + dataclasses"
Task: "T048 FakeZapSignGateway"
```

---

## Implementation Strategy

### MVP First

1. Phase 1 Setup → Phase 2 Foundational.
2. Phase 3 (US1) → **validate**: organization profile CRUD, masked token.
3. Phase 4 (US2) → **validate**: document/signer CRUD + ZapSign submission + `failed`/`resync` +
   cascade delete. This is the demoable MVP (single place to manage documents and send them for
   signature).
4. Stop / demo.

### Incremental Delivery

- + US3: automatic AI insights on each document → demo.
- + US4: authenticated automation API + reports → demo (n8n can now integrate).
- + US5: alerts dashboard → demo (bonus).
- + US6: outbound webhook + example n8n workflow → demo (bonus).
- Phase 9 polish (k8s, README, quickstart validation, coverage/type gates) can be folded in
  progressively; T109–T113 are the release gate.

### Test discipline (constitution Principle II)

- For every task in the "Tests for User Story N" blocks: write it, run it, confirm it **fails**,
  then implement. Third-party APIs (ZapSign, OpenAI, the webhook receiver) are always mocked — the
  suite makes no external network calls, in local and CI.

---

## Notes

- `[P]` = different files, no dependency on an incomplete task.
- `[Story]` labels (US1–US6) map each task to a spec.md user story for traceability.
- Commit after each task or logical group; stop at any checkpoint to validate a story independently.
- `api_token` (ZapSign) is write-only everywhere and absent from every `automation` response —
  enforced by T035, T083, T090, T113.
- `DocumentAnalysis` is append-only: no task adds an update/overwrite path (FR-017).
