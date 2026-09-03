<!--
Sync Impact Report
- Version change: (none) → 1.0.0
- Rationale: Initial ratification of the project constitution (MAJOR baseline).
- Principles defined:
  - I. Clean Architecture & Dependency Inversion
  - II. Test-First for Critical Logic (NON-NEGOTIABLE)
  - III. Simplicity First (KISS / YAGNI)
  - IV. Resilient External Integrations
  - V. Secure, Observable REST API
  - VI. Explicit Domain Data Model
  - VII. Reproducible & Deploy-Ready Environment
- Added sections:
  - Technology & Architecture Constraints
  - Development Workflow & Quality Gates
- Removed sections: none
- Templates / guidance requiring follow-up: none. README.md and PRD.md act as
  runtime development guidance and are referenced by Governance.
- Deferred TODOs: none. RATIFICATION_DATE set to 2026-09-03 (initial adoption for
  this greenfield project).
-->

# Document & Signature Management System Constitution

## Core Principles

### I. Clean Architecture & Dependency Inversion

The backend MUST be organized into separated layers: domain (entities and pure
business rules), application (use cases / services), and infrastructure
(persistence, HTTP, third-party SDKs). Business rules MUST NOT depend on Django or
DRF where isolating them adds real value, and layering MUST NOT be inflated beyond
what the requirement needs.

Every external provider — ZapSign, the LLM/AI analysis provider, n8n webhooks, and
PDF text extraction — MUST be reached only through an explicit interface or gateway
(for example `ZapSignClient`, `AnalysisProvider`). Domain and application code MUST
NOT import a third-party SDK or issue an HTTP call directly.

The backend MUST be split into domain-scoped Django apps (`companies`, `documents`,
`signers`, `integrations`, `automation`, `core`); a single monolithic app is not
permitted.

Rationale: this is what makes the integration components testable, lets providers be
swapped without touching business rules, and keeps the door open to move the AI call
to asynchronous processing later without changing the interface.

### II. Test-First for Critical Logic (NON-NEGOTIABLE)

TDD is mandatory for the components that carry business risk: the ZapSign client,
the AI analysis pipeline, and document/signer status rules. The test MUST be written
first, MUST fail, and only then MUST the implementation be written.

External services (ZapSign, the AI provider) MUST be mocked in tests. CI MUST NEVER
call a real third-party API. Primary API routes and features MUST have automated
tests — Pytest for the backend, Jest for the frontend — and coverage on the primary
routes MUST be at least 80%.

Rationale: the parts most likely to break in production are the integration seams;
they must be pinned by tests before code exists.

### III. Simplicity First (KISS / YAGNI)

The simplest solution that satisfies the requirement MUST be chosen. Asynchronous
processing, queues/workers, caching, and additional abstraction layers MUST NOT be
introduced unless a specific requirement demands them — never preemptively.

Any conscious trade-off made for simplicity (for example, running the AI analysis
synchronously inside the create request) MUST be documented in the README together
with its evolution path.

Rationale: the effort budget must go to the requirements that carry value —
integration, AI analysis, tests — not to speculative scaffolding.

### IV. Resilient External Integrations

Local CRUD MUST continue to work when ZapSign or the AI provider fails (timeout or
error response). A Document MUST be persisted locally before any external call, with
an explicit state (for example `pending_integration` / `failed`).

Every external call MUST have a configurable timeout and explicit failure handling.
A failed AI analysis MUST be retryable via `POST /api/documents/{id}/analyze/`
without recreating the document. A ZapSign failure MUST NOT prevent the document
from being created and retried.

Rationale: third-party availability must never compromise the system of record.

### V. Secure, Observable REST API

Every externally exposed endpoint MUST require authentication: session/token auth
for the internal Angular frontend, and a revocable per-integration API Key
(`Authorization: Api-Key <key>`) for automations. The ZapSign `api_token` MUST NEVER
be exposed to third parties.

The API MUST follow RESTful conventions on DRF (serializers, viewsets/generics,
native authentication). A public `/api/health/` endpoint MUST verify database
connectivity and, where applicable, external-integration status, for Kubernetes
liveness/readiness probes; it MUST NOT require application credentials.

Structured logging MUST be emitted for every external-integration call and every
primary route, capturing response time and status.

Rationale: this is the minimum bar for running the system in production and for
operating it safely.

### VI. Explicit Domain Data Model

All domain entity primary keys MUST be UUID (`uuid4`), never auto-increment
integers. Persistence MUST be PostgreSQL, and every schema change MUST go through a
migration.

Deleting a Document MUST cascade to its Signers. Each AI analysis run MUST create a
new `DocumentAnalysis` record (auditable history); it MUST NOT overwrite a previous
analysis. Read endpoints return the most recent analysis by default, with full
history available via a dedicated endpoint.

Rationale: sequential IDs leak data volume through the API; analysis history must be
auditable.

### VII. Reproducible & Deploy-Ready Environment

The full stack (backend, frontend, database) MUST be dockerized and MUST come up
locally with a single Docker Compose command. Dockerfiles MUST be multi-stage and
Kubernetes-compatible; Kubernetes manifests (Deployment, Service, ConfigMap/Secret,
liveness/readiness probes on `/api/health/`) MUST be delivered, or their omission
MUST be documented in the README as a conscious, time-boxed cut.

The README MUST let any developer set up the project, run the tests, and consume the
endpoints with no additional support. Frontend CRUD MUST be reactive (Angular
components) with no full-page reload.

Rationale: the reviewer must be able to run everything, and the production deploy
path must be unambiguous.

## Technology & Architecture Constraints

The following stack is fixed by the challenge and by closed decisions in the PRD.
Deviating from it requires a justification recorded in the README and a constitution
amendment.

- **Backend:** Django + Django REST Framework, PostgreSQL, UUID primary keys.
- **Frontend:** Angular with reactive components, no page reload on CRUD.
- **AI analysis:** direct OpenAI API call (no LangChain), isolated behind the
  `AnalysisProvider` interface, executed synchronously with a short configurable
  timeout.
- **PDF extraction:** `pypdf` or `pdfplumber`.
- **Automation:** n8n inbound via API Key; outbound via configurable webhook
  (`N8N_WEBHOOK_URL`).
- **Testing:** Pytest (backend, with mocks for ZapSign/OpenAI), Jest (frontend).
- **Design method:** SOLID (dependency inversion at the integration seams),
  lightweight DDD (apps separated by domain), KISS (no complexity not justified by a
  requirement).
- **Infrastructure:** Docker (multi-stage, k8s-ready), Docker Compose for local
  setup, Kubernetes manifests for deployment.
- **Observability:** `/api/health/` health check plus structured logging of
  integration calls and primary routes (response time, status).

Sensitive configuration (`api_token`, OpenAI key, `N8N_WEBHOOK_URL`, database
credentials) MUST be supplied via environment variables / Secrets and MUST NOT be
committed. A `.env.example` MUST be kept current.

## Development Workflow & Quality Gates

- Work follows the build order in PRD section 18.2: scaffolding and Docker first,
  then migrations, then TDD on the integration components, then CRUD, then the
  ZapSign and AI integrations, then health check and logging, then the frontend,
  then the automation endpoints, then end-to-end route tests and the README.
- A change is not "done" until: its tests pass, primary-route coverage remains at or
  above 80%, structured logging and the health check cover any new integration or
  route, and the README reflects any new architecture decision or trade-off.
- Every pull request / review MUST verify compliance with these principles.
  Reviewers MUST reject direct third-party SDK/HTTP usage in domain or application
  code (Principle I) and untested integration or status logic (Principle II).
- Any added complexity MUST be justified in the pull request against Principle III;
  an unjustified queue, cache, or extra layer is grounds to block the change.
- CI MUST run the full Pytest and Jest suites and MUST NOT reach real third-party
  services.

## Governance

This constitution supersedes ad-hoc practices and prior conventions. Where a
requirement in the PRD and a principle here conflict, the conflict MUST be raised
and resolved by amendment before the code is written.

Amendments MUST be made by editing this file, MUST include a Sync Impact Report at
the top, and MUST bump the version according to semantic versioning:

- **MAJOR:** backward-incompatible governance changes, or removal/redefinition of a
  principle.
- **MINOR:** a new principle or section, or materially expanded guidance.
- **PATCH:** clarifications, wording, and non-semantic refinements.

Compliance is reviewed on every pull request. Complexity that cannot be justified
against Principle III MUST be removed or deferred. `README.md` and `PRD.md` are the
runtime development guidance documents and MUST be kept consistent with this
constitution.

**Version**: 1.0.0 | **Ratified**: 2026-09-03 | **Last Amended**: 2026-09-03
