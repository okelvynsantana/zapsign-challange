<!--
Sync Impact Report
- Version change: 1.0.0 → 1.1.0
- Rationale: MINOR. Three new principles and two materially expanded sections govern
  the frontend interface layer, which v1.0.0 covered only by a single clause in
  Principle VII. No existing principle was removed, renamed, or redefined, and no
  prior rule was weakened.
- Principles added:
  - VIII. Token-Driven, Self-Contained Interface
  - IX. Unambiguous Status Vocabulary (NON-NEGOTIABLE)
  - X. Accessible, Localized Frontend
  - XI. Atomic Composition Layers
- Principles modified: none (I–VII unchanged, verbatim)
- Sections expanded:
  - Technology & Architecture Constraints — added the "Frontend interface layer"
    subsection (Angular/SCSS stack, atomic directory convention, token location,
    build budgets, self-hosted fonts)
  - Development Workflow & Quality Gates — added the `data-testid` stability
    contract and the definition of done for an interface change
- Removed sections: none
- Source of the amendment: PRD-DESIGN.md (interface implementation PRD). Only its
  durable, cross-feature rules were promoted here; the implementation itself is a
  feature and is deferred to /speckit-specify.
- Templates / guidance requiring follow-up: none. README.md, PRD.md and PRD-DESIGN.md
  act as runtime development guidance and are referenced by Governance.
- Deferred TODOs: none.
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

### VIII. Token-Driven, Self-Contained Interface

Every colour, type size, spacing step, radius, and control height used by the
frontend MUST resolve from a CSS custom property declared in the global token layer.
Literal design values MUST NOT appear in component styles or templates; the only
permitted exceptions are stroke geometry inside inline SVG and chart-fill values
that are explicitly documented as theme-invariant.

Both a light and a dark theme MUST be defined. Every token MUST have its base
definition in `:root`; a theme variant MUST only *redefine* an existing token. A
colour whose sole definition lives inside a media query or a `[data-theme]` block is
a defect.

The interface MUST NOT take on a component library, a CSS framework, or an icon
library. Icons MUST be inline SVG using `currentColor`. Emoji MUST NOT be used as
interface iconography.

The frontend MUST NOT issue any runtime request to a third-party origin. Fonts and
every other static asset MUST be served from the application's own origin.

Rationale: the tokens are what make two themes and a consistent status vocabulary
achievable at all; the dependency ban keeps the bundle honest and preserves the
system's ability to run with no external network, which Principle IV and the
offline-capable stack already promise.

### IX. Unambiguous Status Vocabulary (NON-NEGOTIABLE)

The system carries three independent status scales, and the interface MUST keep them
visually distinct at all times:

1. **Hand-off** (`provider_status`) — our integration state with ZapSign. This scale
   alone MAY be rendered as a filled, bordered badge, because it is the only state we
   own and the only one with a recovery action.
2. **Signature** (`status`) — reported by ZapSign, never computed locally. It MUST
   NOT be rendered in the hand-off badge form, and an unrecognised value MUST still
   render sensibly rather than break or be dropped.
3. **Analysis** (`latest_analysis`) — a content finding. A risk insight MUST NOT
   share a colour or an icon with a system failure: a risk is a finding about the
   document, a failure is a defect in our processing, and they have different owners
   and different fixes.

No status MAY be communicated by colour alone. Every status indicator MUST combine
colour with a distinct shape or icon and a text label.

Status values that originate in the API (`pending_integration`, `submitted`,
`failed`, `succeeded`, `no_text`, error codes, and the like) MUST be displayed
verbatim as the API emits them, never translated or re-worded, so that the screen,
the logs, and the API documentation always agree.

Rationale: mistaking "sent to ZapSign" for "signed", or a contract risk for a system
error, is the most expensive mistake this interface can invite. The separation is a
correctness property, not a style preference.

### X. Accessible, Localized Frontend

Every interface surface MUST meet WCAG AA contrast in **both** themes: 4.5:1 for
body text and 3:1 for large text and for control borders. Every interactive element
MUST have a visible `:focus-visible` indicator, and every screen MUST be fully
operable by keyboard. Icon-only controls MUST carry an accessible name; decorative
SVG MUST be `aria-hidden`. Form validation errors MUST be associated with their
field programmatically, not only positioned near it.

User-facing copy MUST be written in Brazilian Portuguese. The deliberate exception is
the API-originated technical values covered by Principle IX, which stay verbatim.

Rationale: an internal tool used daily is used by whoever is hired next, on whatever
display and input device they have; accessibility here is a floor, not a feature. A
single interface language keeps the copy reviewable.

### XI. Atomic Composition Layers

The frontend component tree MUST be organized by Atomic Design layers, and the
dependency direction between layers MUST be one-way — a lower layer MUST NOT import
from a higher one:

1. **Atoms** — indivisible UI primitives (badge, button, field, chip, card, empty
   state). They MUST NOT import a domain model, inject a service, or issue an HTTP
   call. An atom that carries no behaviour and no accessible semantics SHOULD be a
   global SCSS class rather than an Angular component, so that the per-component
   style budget of Principle VIII is not spent on duplication; an atom with
   behaviour or with semantics of its own MUST be a component.
2. **Molecules** — an atom bound to one domain value (the hand-off badge, the
   signature marker, the analysis marker, a signer row). They MAY depend on the
   types in `core/models/`; they MUST NOT inject a service or fetch data.
3. **Organisms** — self-contained regions of a screen that MAY own local state and
   MAY inject services (the documents table, the detail rail, the analysis panel,
   the creation form, an alerts group).
4. **Pages** — the routed components. They own routing, data fetching, and
   orchestration, and delegate rendering to organisms. A page MUST NOT contain
   markup that belongs to a lower layer.

Every element MUST live at the lowest layer its dependencies permit. Promoting an
element to a higher layer because it was convenient to place it there is a defect;
so is a lower-layer element that reaches upward for a service or a page's state.

Rationale: the same status indicators, fields, and empty states recur across every
screen. Layering them with a one-way dependency rule is what keeps them genuinely
reusable and independently testable, and it is the same dependency-inversion
discipline Principle I imposes on the backend, applied to the interface.

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

### Frontend interface layer

- **Styling:** hand-written SCSS on Angular standalone components. No component
  library, no CSS framework, no icon package (Principle VIII).
- **Layers:** reusable atoms, molecules, and organisms live under
  `frontend/src/app/ui/{atoms,molecules,organisms}/`. A routed page stays in its
  feature folder (`documents/`, `companies/`, `reports/`, `alerts/`) together with the
  organisms used only by that feature. `core/` keeps models, services, and guards and
  belongs to no visual layer.
- **Tokens:** the token layer, reset, typography, and shared UI atoms live in global
  stylesheets imported from `frontend/src/styles.scss`. Component stylesheets carry
  only that screen's layout and MUST consume tokens via `var(--token)`.
- **Build budgets:** the budgets configured in `angular.json` are binding — 500 kB
  warning on the initial bundle, and 4 kB warning / 8 kB error on any single
  component stylesheet. Duplicating shared atoms per component is the usual cause of
  a breach and MUST be resolved by promoting the atom, not by raising the budget.
- **Fonts:** self-hosted and version-pinned, limited to the weights actually used,
  with an explicit fallback stack on every declaration.
- **Layout:** sibling groups MUST be laid out with flex or grid plus `gap`, not with
  per-element margins. No screen may scroll horizontally; wide content scrolls inside
  its own container.

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
- `data-testid` attributes are a stable test contract. Restyling or restructuring a
  template MUST preserve the existing identifiers on the equivalent elements. An
  identifier MAY be removed only together with the test that reads it, and the
  removal MUST be called out in the pull request.
- An interface change is not "done" until it has been seen in both themes, meets the
  contrast and keyboard requirements of Principle X, keeps the status vocabulary of
  Principle IX intact, and builds within the configured budgets.
- Every pull request / review MUST verify compliance with these principles.
  Reviewers MUST reject direct third-party SDK/HTTP usage in domain or application
  code (Principle I), untested integration or status logic (Principle II), literal
  design values or a new UI dependency (Principle VIII), any status rendered by
  colour alone (Principle IX), and any component that imports from a higher atomic
  layer than its own (Principle XI).
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
against Principle III MUST be removed or deferred. `README.md`, `PRD.md` and
`PRD-DESIGN.md` are the runtime development guidance documents and MUST be kept
consistent with this constitution.

**Version**: 1.1.0 | **Ratified**: 2026-09-03 | **Last Amended**: 2026-09-08
