# Phase 0 Research: Document & Signature Management System

**Feature**: `001-document-signature-management` | **Date**: 2026-09-03

All items below were either fixed by `PRD.md` / the `/speckit-plan` input or are low-risk defaults.
No open `NEEDS CLARIFICATION` remains. Format per decision / rationale / alternatives.

---

## 1. Backend language & framework version

- **Decision**: Python 3.12, Django 5.x LTS, Django REST Framework (latest stable).
- **Rationale**: Django + DRF are mandated (PRD RNF08, plan input). Python 3.12 is a widely
  available stable release with mature typing support (`type` statement, better generics) and full
  ecosystem coverage for `django-stubs`. Django 5.x LTS gives the longest support window and native
  `UUIDField` PK support with no extra library (PRD §18.3).
- **Alternatives considered**: Python 3.13 (very new; some C-extension / stub lag — rejected for
  stability); FastAPI (rejected — DRF is mandated and gives serializers/viewsets/auth out of the box).

## 2. Internal user authentication (SPA → backend)

- **Decision**: `djangorestframework-simplejwt` — access + refresh tokens, `POST /api/auth/token/`
  and `/api/auth/token/refresh/`. Single internal user seeded via migration/management command.
- **Rationale**: PRD §10.4 selects "session/token simple auth" for the frontend and single-tenant
  usage. JWT is stateless (fits horizontally scaled k8s pods with no shared session store), is
  trivial to consume from an Angular `HttpInterceptor`, and needs no sticky sessions or Redis.
- **Alternatives considered**: Django session auth (needs shared session backend across pods or
  sticky ingress — extra moving part, violates KISS for the deploy target); DRF `TokenAuthentication`
  (no expiry/refresh semantics); OAuth2 provider (overkill for one internal user — PRD §10.4).

## 3. Automation / n8n authentication (external callers → backend)

- **Decision**: `djangorestframework-api-key` — header `Authorization: Api-Key <key>`. Keys are
  hashed at rest, carry a name, and are individually revocable. Applied only to `apps/automation`
  endpoints via a dedicated permission class.
- **Rationale**: PRD §10.4 explicitly chooses a revocable per-integration API key over JWT for n8n
  (lower friction in an HTTP Request node, rotatable, never involves the ZapSign `api_token`). The
  library provides hashing, prefix lookup, admin management, and a permission class — less custom
  crypto to own (KISS, Principle II testability).
- **Alternatives considered**: Hand-rolled API-key model + auth backend (more code to test for no
  gain); reusing JWT for n8n (rejected by PRD §10.4); HMAC-signed requests (more integration
  friction, unnecessary for a trusted internal automation host).

## 4. AI analysis provider & model

- **Decision**: OpenAI via the official `openai` Python SDK, called directly (no LangChain). Default
  model `gpt-4o-mini`, configurable via `AI_MODEL`. Request JSON output with a strict response
  schema (`response_format` / structured outputs) for `summary`, `missing_topics`, `insights`.
- **Rationale**: PRD §10.2 is a closed decision — OpenAI, direct call, no LangChain, documents
  largely in Portuguese. `gpt-4o-mini` is low-cost, fast (helps the 15 s synchronous budget,
  SC-003), and strong on pt-BR summarisation/judgement. Structured outputs remove brittle parsing.
- **Alternatives considered**: `gpt-4o` (higher quality, higher latency/cost — not justified for
  this scope; model is a config swap if needed); spaCy / HuggingFace (rejected in PRD §10.2 — NLP
  vs. content judgement, infra/latency cost); LangChain (rejected in PRD §10.2 — orchestration
  layer with no value for one structured prompt).

## 5. PDF text extraction

- **Decision**: `pypdf` behind a `PdfTextExtractor` ABC. Fetch the PDF from the provided URL with a
  bounded `httpx` timeout and a max-size guard, then extract text. Scanned/image-only PDFs (no
  extractable text) → analysis marked `failed` with reason `no_extractable_text`.
- **Rationale**: PRD §10.2 lists `pypdf` or `pdfplumber`; `pypdf` is the lighter dependency and is
  sufficient for text-based contract PDFs. KISS (Principle III): one library, added complexity only
  if a real document needs it. The ABC keeps the swap cheap and the pipeline testable with a fake.
- **Alternatives considered**: `pdfplumber` (better tables/layout, heavier, slower — kept as the
  documented fallback if extraction quality proves insufficient); OCR (`pytesseract`) for scanned
  PDFs (out of scope — spec treats image-only PDFs as "no extractable text").

## 6. Missing-clause reinforcement

- **Decision**: After the LLM call, run a regex/keyword pass for common Brazilian contract clauses
  (rescisão, foro, vigência, confidencialidade, multa, objeto, pagamento, LGPD/dados pessoais).
  Merge findings; record `source` as `llm`, `regex`, or `llm+regex` on the `DocumentAnalysis`.
- **Rationale**: PRD §10.2 pipeline step 3 — an independent validation layer that does not depend on
  the model "remembering" to check everything; also a graceful-degradation path (regex-only result
  if the LLM returns partial data). The clause list is a configurable default (spec Assumptions).
- **Alternatives considered**: LLM-only (single point of failure for completeness — rejected by
  PRD); a second LLM "critic" call (doubles latency/cost against the 15 s budget — rejected, KISS).

## 7. Analysis execution mode

- **Decision**: Synchronous — the analysis runs inside the `POST /api/documents/` and
  `POST /api/documents/{id}/analyze/` request, with a configurable timeout (`AI_TIMEOUT_SECONDS`,
  default 15). No task queue.
- **Rationale**: PRD §10.2 / §18.1 closed decision, justified by KISS (Principle III): async is only
  introduced when a requirement demands scale. The `AnalysisProvider` interface is designed so a
  future move to a queue changes only the caller, not the contract. README documents the trade-off
  and evolution path (Principle III requirement).
- **Alternatives considered**: Celery + Redis worker (extra services in Compose and k8s, more to
  test/operate — not justified at this scale); Django background task / thread (hidden failure
  modes, no retry/visibility — rejected).

## 8. Resilience pattern for external calls

- **Decision**: `DocumentService.create` persists the `Document` row (`provider_status =
  pending_integration`) and its `Signer` rows in a transaction **before** any outbound call. ZapSign
  is then called; success updates `open_id`/`token`/`status`/`provider_status = submitted`, failure
  sets `provider_status = failed` (document kept). AI analysis is then attempted; failure writes a
  `DocumentAnalysis(state = failed, error_reason = ...)`. Retries: `POST /api/documents/{id}/resync/`
  (ZapSign) and `POST /api/documents/{id}/analyze/` (AI). Every outbound call uses `httpx` connect/
  read timeouts from typed settings.
- **Rationale**: Constitution Principle IV and PRD RNF04 / §15 — third-party availability must never
  compromise the system of record. Local-first write + explicit failure state + idempotent retry is
  the standard resilient-integration shape and is fully testable with mocked gateways.
- **Alternatives considered**: Call ZapSign first, then save (loses the document on provider failure
  — rejected by PRD §15); automatic background retry (needs a scheduler — deferred, manual retry
  endpoint is sufficient for the challenge, KISS).

## 9. Typing & static analysis

- **Decision**: Full type hints on all backend public functions, methods, domain dataclasses, and
  service signatures. `mypy` in CI with `django-stubs` + `djangorestframework-stubs`, run in a
  pragmatic-strict mode (`disallow_untyped_defs`, `warn_unused_ignores`, `no_implicit_optional`;
  `strict` relaxed only where Django dynamic attributes force it). `ruff` for lint + format.
- **Rationale**: Explicit plan input ("quero que use também tipagem para que possamos ter o controle
  do que se espera nos métodos e entidades"). Frozen `@dataclass` domain entities with typed fields
  give the "control over what methods and entities expect" the user asked for and make the domain
  layer verifiable independently of Django. `ruff` replaces flake8+isort+black (one fast tool, KISS).
- **Alternatives considered**: `pyright` (excellent, but `mypy` + `django-stubs` is the better-trodden
  path for Django); `strict = true` everywhere (too much friction against Django's dynamic ORM
  attributes for a time-boxed build — pragmatic strict chosen).

## 10. Structured logging & observability

- **Decision**: stdlib `logging` with `python-json-logger` JSON formatter. A `RequestTimingLogger`
  middleware logs method, path, status, and `elapsed_ms` for every request. A `@log_gateway_call`
  decorator wraps each gateway method (ZapSign, OpenAI, PDF fetch, webhook) logging provider,
  operation, outcome, and `elapsed_ms`. Correlation id per request added to the log context.
- **Rationale**: PRD RNF17 / Constitution Principle V — structured logs on integration calls and
  primary routes with status + timing, as the minimum production observability bar. Stdlib + one
  formatter keeps it dependency-light (KISS).
- **Alternatives considered**: `structlog` (nicer API, extra dependency and config — not worth it at
  this size); OpenTelemetry traces/metrics (valuable but beyond the challenge's "basic
  observability" ask — noted as future work in README).

## 11. Health check

- **Decision**: `GET /api/health/` (unauthenticated) returns `200` with
  `{"status": "ok", "checks": {"database": "ok", "zapsign": "ok|skipped|error",
  "openai": "ok|skipped|error"}}` and `503` if the database check fails. External-provider checks
  are best-effort and time-boxed; their failure does not fail the endpoint (only DB does).
- **Rationale**: PRD RNF16 / Constitution Principle V — used by k8s liveness/readiness probes,
  which must not depend on app credentials or on third-party uptime. DB reachability is the true
  readiness signal for this service.
- **Alternatives considered**: `django-health-check` package (pulls in more checks than needed —
  a ~30-line view is clearer and fully under test); making provider checks fatal (would let a
  ZapSign outage cycle our pods — rejected).

## 12. Containerisation & Kubernetes manifests

- **Decision**: Multi-stage `Dockerfile` per service (build stage with full toolchain → slim
  non-root runtime; backend runtime runs `gunicorn`, frontend runtime is `nginx` serving the built
  Angular bundle). `deploy/docker-compose.yml` brings up postgres + backend + frontend + a one-shot
  migrate service with a single `docker compose up`. `deploy/k8s/` uses **Kustomize** — a `base/`
  (Deployments, Services, ConfigMap, Secret placeholder, Ingress, liveness/readiness probes on
  `/api/health/`, resource requests/limits) and `overlays/local` + `overlays/prod`.
- **Rationale**: PRD RNF03 / RNF15 / Constitution Principle VII — one-command local stack plus
  k8s-ready images and manifests. Kustomize is built into `kubectl` (no extra tool like Helm to
  install or template-debug — KISS), and overlays cleanly express local vs. prod differences.
- **Alternatives considered**: Helm chart (more powerful, more ceremony/templating — PRD allows
  "manifests or Helm chart"; Kustomize chosen for simplicity); single-stage Dockerfiles (larger
  images, build tools shipped to prod — rejected); running Angular via Node in prod (nginx static
  serving is lighter and standard).

## 13. CI pipeline (GitHub Actions)

- **Decision**: Three workflows on push / PR:
  - `backend.yml`: set up Python 3.12 → install → `ruff check` + `ruff format --check` → `mypy` →
    `pytest --cov --cov-fail-under=80` against a `postgres:16` service container. No network to
    third parties (providers are mocked).
  - `frontend.yml`: set up Node 20 → `npm ci` → `eslint` → `jest --coverage` → `npm run build`.
  - `images.yml`: build backend + frontend images (Buildx, layer cache); push to GHCR only on the
    default branch / tags (guarded, opt-in).
- **Rationale**: Explicit plan input ("estruture uma esteira com github actions"). Splitting by
  surface keeps runs fast and independently signalling. Coverage gate enforces Constitution
  Principle II's ≥80% on primary flows. Mock-only tests satisfy "CI never calls third parties".
- **Alternatives considered**: One monolithic workflow (slower feedback, noisier logs); pushing
  images on every branch (registry churn — restricted to default branch/tags); running real
  provider integration in CI (violates Principle II — excluded).

## 14. Frontend framework version & test runner

- **Decision**: Angular 19 with standalone components, typed reactive forms, and signals for view
  state; Jest (`jest-preset-angular`) as the test runner.
- **Rationale**: Angular is mandated (PRD RNF07). v19 standalone + signals give reactive,
  no-reload list updates (SC-004) with less boilerplate than NgModules. PRD §12 names Jest for
  frontend tests; Jest is faster and less flaky in CI than Karma/ChromeHeadless.
- **Alternatives considered**: Karma + Jasmine (Angular default; heavier in CI — rejected per PRD's
  Jest choice); NgModule architecture (more boilerplate, no benefit for a small SPA).

## 15. Reports

- **Decision**: Per-document report `GET /api/documents/{id}/report/` → document status +
  `provider_status` + most recent `DocumentAnalysis`. Aggregated report
  `GET /api/reports/summary/` → counts of documents grouped by signature status and by
  `provider_status`, total documents, count with a risk insight in their latest analysis, and the N
  most recent risk insights. Both require auth (JWT or API key). Computed with ORM aggregation, no
  materialised store.
- **Rationale**: PRD RF10 / §11 / spec US4 — reports must be consumable by automation and reflect
  live data. At this scale a direct aggregate query per request is well under the latency budget;
  caching would be premature (KISS).
- **Alternatives considered**: Precomputed/materialised report table (needs invalidation logic —
  unjustified at this volume); background report generation (async infra not warranted).

---

## Open questions

None. All Technical Context entries are resolved; Phase 1 may proceed.
