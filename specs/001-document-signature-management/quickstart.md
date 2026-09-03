# Quickstart & Validation Guide: Document & Signature Management System

**Feature**: `001-document-signature-management` | **Date**: 2026-09-03

This guide proves the feature works end-to-end. It is a run/validation reference — implementation
details live in `tasks.md` and the code. Commands assume repo root and Docker + Docker Compose v2.

Related: [`plan.md`](./plan.md) · [`data-model.md`](./data-model.md) ·
[`contracts/rest-api.md`](./contracts/rest-api.md) · [`contracts/openapi.yaml`](./contracts/openapi.yaml)

---

## 0. Prerequisites

| Need | Version | Notes |
|---|---|---|
| Docker + Compose v2 | recent | the only hard requirement for the happy path |
| ZapSign sandbox account | — | provides the `api_token` stored on the Company row |
| OpenAI API key | — | for real analysis; without it, use the regex fallback or the fake provider |
| (dev only) Python 3.12, Node 20 | | to run suites outside containers |

Copy and fill environment:

```bash
cp deploy/.env.example deploy/.env
# set at minimum: POSTGRES_* , DJANGO_SECRET_KEY , OPENAI_API_KEY (optional), ZAPSIGN_BASE_URL
```

Every variable in `deploy/.env.example` is documented inline (Constitution Principle VII).

---

## 1. Bring the stack up (target: < 10 min from clone — SC-008)

```bash
docker compose -f deploy/docker-compose.yml up --build
```

This starts: `db` (PostgreSQL 16), `migrate` (one-shot `manage.py migrate` + seed of one internal
user and, optionally, one Company), `backend` (Django/gunicorn on `:8000`), `frontend` (nginx
serving the Angular build on `:4200`).

Verify health (unauthenticated — FR-027):

```bash
curl -s localhost:8000/api/health/ | jq
# expect: {"status":"ok","checks":{"database":"ok", ...}}
```

Open the SPA at <http://localhost:4200>.

---

## 2. Authenticate

Internal user (SPA / manual calls):

```bash
ACCESS=$(curl -s localhost:8000/api/auth/token/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"manager","password":"manager"}' | jq -r .access)
```

Automation key (created by seed or `manage.py create_api_key "n8n"`; the plaintext is printed
once): export it as `APIKEY`.

---

## 3. User Story validations

### US1 — Organization profile & credentials (P1)

```bash
# create
COMPANY=$(curl -s localhost:8000/api/companies/ -H "Authorization: Bearer $ACCESS" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Acme Ltda","api_token":"<zapsign-sandbox-token>"}' | jq -r .id)

# response must NOT contain api_token, only api_token_masked   (FR-002)
curl -s localhost:8000/api/companies/$COMPANY/ -H "Authorization: Bearer $ACCESS" | jq

# edit name without resending the token (token is preserved)
curl -s -X PATCH localhost:8000/api/companies/$COMPANY/ -H "Authorization: Bearer $ACCESS" \
  -H 'Content-Type: application/json' -d '{"name":"Acme S.A."}' | jq

# delete is blocked once it has a document (run after US2) -> 409 company_has_documents  (FR-004)
```

**Pass when**: create/edit/delete round-trips; `api_token` never appears in any response; delete
with a document returns `409`.

### US2 — Documents, signers, automatic ZapSign submission (P1)

```bash
DOC=$(curl -s localhost:8000/api/documents/ -H "Authorization: Bearer $ACCESS" \
  -H 'Content-Type: application/json' -d '{
    "company":"'"$COMPANY"'",
    "name":"Contrato de Prestação de Serviços",
    "pdf_url":"https://<public-url>/contrato.pdf",
    "signers":[{"name":"Ana Souza","email":"ana@example.com"}]
  }' | jq -r .id)

curl -s localhost:8000/api/documents/$DOC/ -H "Authorization: Bearer $ACCESS" | jq
```

**Pass when**:

- Response is `201` and the document is retrievable **even if** ZapSign is down — then
  `provider_status="failed"` and `last_provider_error` is set (FR-008, FR-010).
- With ZapSign reachable: `provider_status="submitted"`, `open_id`, `token`, and `status` populated;
  signer `token`/`status` populated (FR-009).
- Retry path: `curl -X POST .../api/documents/$DOC/resync/` moves `failed` → `submitted` (FR-010).
- `PATCH` on `name` / `pdf_url` / `signers` persists (FR-005, FR-006).
- `DELETE .../api/documents/$DOC/` returns `204`; afterwards
  `GET /api/signers/?document=$DOC` is empty (FR-011, SC-005).
- Two signers with the same email in one payload → `400` with `fields.email` (edge case).
- SPA: creating/editing/deleting updates the list with no full-page reload (FR-012, SC-004).

### US3 — Automatic AI analysis (P2)

```bash
# latest analysis is embedded on the document after creation
curl -s localhost:8000/api/documents/$DOC/ -H "Authorization: Bearer $ACCESS" | jq .latest_analysis

# trigger a fresh run -> a NEW analysis row (does not overwrite)
curl -s -X POST localhost:8000/api/documents/$DOC/analyze/ -H "Authorization: Bearer $ACCESS" | jq

# full history, newest first
curl -s localhost:8000/api/documents/$DOC/analyses/ -H "Authorization: Bearer $ACCESS" | jq '.results | length'
```

**Pass when**:

- A successful analysis has `state="succeeded"`, non-empty `summary`, `missing_topics` array,
  `insights` array, `source` in `llm|regex|llm+regex` (FR-014, FR-021).
- Calling `analyze` again increases the history count by exactly 1; the earlier row is unchanged
  (FR-017); `latest_analysis` reflects the newest (FR-018).
- Unreachable / image-only `pdf_url` → `state="failed"` with `error_reason`, and the **document is
  still intact** with its ZapSign fields untouched (FR-019, FR-020, SC-010).
- Provider outage with regex fallback enabled → `state="succeeded"`, `source="regex"` (research §6).

### US4 — Authenticated programmatic access (P2)

```bash
# create via automation namespace with the API key
curl -s localhost:8000/api/automation/documents/ -H "Authorization: Api-Key $APIKEY" \
  -H 'Content-Type: application/json' -d '{ "company":"'"$COMPANY"'", "name":"Via n8n",
      "pdf_url":"https://<public-url>/x.pdf", "signers":[{"name":"Bo","email":"bo@e.com"}] }' | jq -r .id

curl -s -X POST localhost:8000/api/automation/documents/$DOC/analyze/ -H "Authorization: Api-Key $APIKEY" | jq .state
curl -s localhost:8000/api/automation/documents/$DOC/report/ -H "Authorization: Api-Key $APIKEY" | jq
curl -s localhost:8000/api/automation/reports/summary/ -H "Authorization: Api-Key $APIKEY" | jq

# negative checks
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/api/automation/reports/summary/                       # 401
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/api/automation/reports/summary/ -H "Authorization: Bearer $ACCESS"  # 401/403 (JWT not accepted here)
# revoke the key (manage.py revoke_api_key <prefix>) then repeat -> 403, no body data
```

**Pass when**: all four automation calls succeed with a valid key; every call with no key, a JWT, a
malformed key, or a revoked key is rejected with no document/report data (FR-022, FR-023, FR-024,
SC-006, SC-007). Per-doc report contains status + latest analysis (FR-025); summary groups by status
and lists risk insights (FR-026).

### US5 — Alerts dashboard (P3, bonus)

```bash
# with ALERT_STALLED_DAYS lowered for the demo, or a back-dated document:
curl -s localhost:8000/api/alerts/ -H "Authorization: Bearer $ACCESS" | jq
```

**Pass when**: a document older than the threshold appears as a `stalled` alert; a document whose
latest analysis has a `risk=true` insight appears as a `risk` alert; no matches → an empty list,
not an error (FR-030, US5 AS-3, SC-011).

### US6 — Outbound automation webhook (P3, bonus)

```bash
# point N8N_WEBHOOK_URL at a request-bin style receiver, then cause a status change / risk analysis
# and inspect the received body against contracts/webhook-outbound.md
```

**Pass when**: a `document.status_changed` / `document.analyzed` payload matching the contract is
delivered; pointing the URL at an unreachable host leaves `POST /api/documents/` and
`POST /api/documents/{id}/analyze/` fully working (FR-031, FR-032).

---

## 4. Run the test suites

Backend (inside the container or a local venv):

```bash
docker compose -f deploy/docker-compose.yml run --rm backend \
  bash -lc "ruff check . && ruff format --check . && mypy . && pytest --cov --cov-fail-under=80"
```

- TDD components (ZapSign gateway, PDF extractor, analysis pipeline/provider, status rules) have
  tests written before implementation; third-party APIs are mocked — the suite makes **no external
  network calls** (Constitution Principle II).
- Coverage gate: ≥ 80 % on the primary-flow packages (SC-009).

Frontend:

```bash
docker compose -f deploy/docker-compose.yml run --rm frontend \
  bash -lc "npm run lint && npm test -- --coverage"
```

---

## 5. Kubernetes deploy check

```bash
kubectl apply -k deploy/k8s/overlays/local
kubectl -n docsign rollout status deploy/backend deploy/frontend
kubectl -n docsign get pods            # backend/frontend Ready via probes on /api/health/
kubectl -n docsign port-forward svc/backend 8000:8000 &
curl -s localhost:8000/api/health/ | jq
```

**Pass when**: both Deployments become Ready (liveness/readiness probes hit `/api/health/`),
config/secrets come from ConfigMap/Secret, and the health endpoint responds through the Service
(Constitution Principle VII, PRD RNF15/RNF16).

---

## 6. CI expectation (GitHub Actions)

On every push / PR:

- `backend.yml` — `ruff` + `mypy` + `pytest` (with a `postgres:16` service) + coverage gate; no
  third-party network.
- `frontend.yml` — `eslint` + `jest --coverage` + `npm run build`.
- `images.yml` — build backend + frontend images; push to GHCR only on the default branch / tags.

A green pipeline on a fresh clone is the acceptance signal for the "reproducible environment"
requirement.

---

## Definition of done for this feature

- [ ] `docker compose up` yields a working SPA + API + DB in one command.
- [ ] All six User Story validation blocks above pass (US5/US6 may be partial — bonus).
- [ ] ZapSign and AI failures never lose or corrupt a local document (SC-002, SC-010).
- [ ] `api_token` never appears in an API response; automation endpoints reject non-API-key auth.
- [ ] Backend `ruff` + `mypy` clean; `pytest` green with ≥ 80 % coverage on primary flows; Jest green.
- [ ] `kubectl apply -k deploy/k8s/overlays/local` brings both Deployments Ready.
- [ ] README documents setup, tests, endpoints, the AI pipeline, and the SOLID/DDD/KISS/UUID and
      sync-AI trade-off decisions.
