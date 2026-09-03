# Contract: External REST API

**Feature**: `001-document-signature-management` | **Base path**: `/api/` | **Format**: JSON

This is the human-readable companion to [`openapi.yaml`](./openapi.yaml). It defines the endpoints
the backend exposes to the Angular SPA and to external automation callers. Internal gateway
interfaces (ZapSign, AI) are in separate contract files.

---

## Authentication

| Scheme | Header | Used by | Applies to |
|---|---|---|---|
| JWT (access token) | `Authorization: Bearer <access>` | Angular SPA (internal manager) | all `/api/**` except `/api/health/` and `/api/auth/**` |
| API key | `Authorization: Api-Key <key>` | external automation (n8n) | `/api/automation/**` (also accepted on the shared document/report reads) |
| none | — | infra probes | `/api/health/` only |

- Missing / malformed / expired / revoked credential ⇒ `401` (unauthenticated) or `403` (revoked
  key), **no resource data in the body** (FR-023).
- The ZapSign `api_token` is never present in any response of this API (FR-002).
- `/api/automation/**` accepts **only** the API-key scheme; a JWT is rejected there and vice-versa,
  so an integration key can never act as a full SPA session.

## Conventions

- IDs are UUID strings. Timestamps are ISO-8601 UTC.
- List endpoints are paginated: `?page=<n>&page_size=<1..100>` →
  `{ "count": int, "next": url|null, "previous": url|null, "results": [...] }`.
- Mutations return the full resource representation so the SPA can update its store without a reload
  (FR-012).
- Standard error body:

  ```json
  { "detail": "human readable message", "code": "machine_slug", "fields": { "pdf_url": ["Enter a valid URL."] } }
  ```

  `fields` present only for `400` validation errors.
- Status codes: `200` ok, `201` created, `204` deleted, `400` validation, `401` unauthenticated,
  `403` forbidden/revoked, `404` not found, `409` conflict (e.g. company with documents),
  `422` never used (validation is `400`), `502` external provider hard failure surfaced explicitly
  only where noted, `503` health only.

---

## Auth endpoints

### `POST /api/auth/token/`
Body `{ "username": str, "password": str }` → `200 { "access": str, "refresh": str }` |
`401 { "detail": "No active account found with the given credentials", "code": "invalid_credentials" }`.

### `POST /api/auth/token/refresh/`
Body `{ "refresh": str }` → `200 { "access": str }` | `401`.

---

## Health

### `GET /api/health/`  *(unauthenticated)*
- `200`:
  ```json
  { "status": "ok",
    "checks": { "database": "ok", "zapsign": "ok|skipped|error", "openai": "ok|skipped|error" } }
  ```
- `503 { "status": "unavailable", "checks": { "database": "error", ... } }` — only when the DB check
  fails. Provider check failures do **not** cause `503` (FR-027, research §11).

---

## Companies  *(JWT)*

Resource:

```json
{ "id": "uuid", "name": "Acme Ltda", "api_token_masked": "••••••3f9a",
  "created_at": "...", "last_updated_at": "..." }
```

`api_token` is **write-only** (accepted on create/update, never returned).

| Method | Path | Body | Success | Errors |
|---|---|---|---|---|
| GET | `/api/companies/` | — | `200` list | `401` |
| POST | `/api/companies/` | `{ "name", "api_token" }` | `201` resource | `400` |
| GET | `/api/companies/{id}/` | — | `200` resource | `401`, `404` |
| PUT/PATCH | `/api/companies/{id}/` | `{ "name", "api_token"? }` | `200` resource | `400`, `404` |
| DELETE | `/api/companies/{id}/` | — | `204` | `404`; `409 { "code": "company_has_documents" }` (FR-004) |

- On update, omitting `api_token` (or sending `""`) keeps the stored value (data-model validation).

---

## Documents  *(JWT; POST/report/analyze/analyses also reachable via API key — see Automation)*

Resource:

```json
{ "id": "uuid",
  "company": "uuid",
  "name": "Contrato X",
  "pdf_url": "https://.../x.pdf",
  "external_id": "opt-ref",
  "provider_status": "pending_integration | submitted | failed",
  "status": "pending",                     // ZapSign signature status, may be null
  "open_id": 123456,                        // may be null
  "token": "zapsign-doc-token",            // may be null
  "created_by": "manager",
  "last_provider_error": null,
  "signers": [ { "id": "uuid", "name": "Ana", "email": "ana@x.com",
                "status": "pending", "token": null, "external_id": null } ],
  "latest_analysis": { /* DocumentAnalysis resource, or null */ },
  "created_at": "...", "last_updated_at": "..." }
```

### `GET /api/documents/`
`200` paginated list. Query filters: `?provider_status=`, `?status=`, `?company=`, `?has_risk=true`.

### `POST /api/documents/`
Create a document, its signers, submit to ZapSign, then run analysis — all in the single request
(FR-007, FR-008, FR-009, FR-014).

Request:

```json
{ "company": "uuid",
  "name": "Contrato X",
  "pdf_url": "https://.../x.pdf",
  "external_id": "opt-ref",
  "signers": [ { "name": "Ana", "email": "ana@x.com" } ] }   // >= 1 required
```

Responses:

- `201` with the full resource.
  - ZapSign OK ⇒ `provider_status="submitted"`, `open_id`/`token`/`status` populated.
  - ZapSign failed/timed out ⇒ `provider_status="failed"`, `last_provider_error` set, document still
    returned (FR-010). The `201` still stands — the local resource was created.
  - Analysis OK ⇒ `latest_analysis.state="succeeded"`. Analysis failed ⇒
    `latest_analysis.state="failed"` with `error_reason`; document unaffected (FR-019, FR-020).
- `400` — missing/invalid fields, empty `signers`, duplicate signer email within the payload,
  unknown `company`.

### `GET /api/documents/{id}/`
`200` resource | `404`.

### `PUT/PATCH /api/documents/{id}/`
Editable: `name`, `pdf_url`, `external_id`, and nested `signers` (add/edit/remove) (FR-005, FR-006).
`provider_status`, `status`, `open_id`, `token` are read-only here. `200` resource | `400` | `404`.

### `DELETE /api/documents/{id}/`
`204`. Cascades to signers and analyses (FR-011, FR-017). | `404`.

### `POST /api/documents/{id}/resync/`
Re-submit to / refresh from ZapSign (FR-010). Allowed when `provider_status` is `failed` or
`submitted`; `409 { "code": "resync_not_allowed" }` otherwise (e.g. an attempt already in flight).
`200` with updated document (`provider_status` → `submitted` or `failed`).

### `POST /api/documents/{id}/analyze/`
Create a **new** analysis run for the document (FR-016, FR-017). `201` with the new
`DocumentAnalysis` resource (`state` `succeeded` or `failed`). `404` if the document is gone.
Never overwrites earlier analyses.

### `GET /api/documents/{id}/analyses/`
`200` paginated history, newest first (FR-018). Each item is a `DocumentAnalysis` resource.

### `GET /api/documents/{id}/report/`
`200` per-document report (FR-025, US4 AS-3):

```json
{ "document_id": "uuid", "name": "Contrato X",
  "provider_status": "submitted", "signature_status": "pending",
  "signers": [ { "name": "Ana", "email": "ana@x.com", "status": "pending" } ],
  "latest_analysis": { /* DocumentAnalysis or null */ },
  "created_at": "...", "last_updated_at": "..." }
```

`DocumentAnalysis` resource shape:

```json
{ "id": "uuid", "state": "succeeded | failed",
  "summary": "…", "missing_topics": ["rescisão", "foro"],
  "insights": [ { "text": "Cláusula de multa desproporcional", "risk": true } ],
  "source": "llm | regex | llm+regex", "model": "gpt-4o-mini",
  "error_reason": null, "created_at": "..." }
```

---

## Signers  *(JWT)*

Standalone endpoints in addition to nested management inside a document (FR-006).

| Method | Path | Body | Success | Errors |
|---|---|---|---|---|
| GET | `/api/signers/?document={id}` | — | `200` list | `401` |
| POST | `/api/signers/` | `{ "document", "name", "email", "external_id"? }` | `201` | `400` (dup email on that document → `fields.email`) |
| GET | `/api/signers/{id}/` | — | `200` | `404` |
| PUT/PATCH | `/api/signers/{id}/` | `{ "name"?, "email"?, "external_id"? }` | `200` | `400`, `404` |
| DELETE | `/api/signers/{id}/` | — | `204` | `404` |

---

## Reports  *(JWT or API key)*

### `GET /api/reports/summary/`
Aggregated report across all documents (FR-026, US4 AS-4):

```json
{ "total_documents": 42,
  "by_provider_status": { "pending_integration": 1, "submitted": 39, "failed": 2 },
  "by_signature_status": { "pending": 30, "signed": 9, "refused": 1, "unknown": 2 },
  "documents_with_risk_insight": 5,
  "recent_risk_insights": [
    { "document_id": "uuid", "name": "Contrato X", "text": "…", "created_at": "..." }
  ],
  "generated_at": "..." }
```

`200` always (empty dataset ⇒ zeros and empty arrays, still well-formed — edge case).

---

## Automation namespace  *(API key only)*

Thin, stable surface for n8n. Reuses the same service layer as the SPA endpoints; responses never
include `api_token` or JWT-only fields.

| Method | Path | Purpose | Maps to |
|---|---|---|---|
| POST | `/api/automation/documents/` | create a document (+ZapSign +analysis) | same as `POST /api/documents/` (FR-022) |
| POST | `/api/automation/documents/{id}/analyze/` | trigger a fresh analysis | same as `POST /api/documents/{id}/analyze/` (FR-022) |
| GET | `/api/automation/documents/{id}/report/` | per-document report | same as `GET /api/documents/{id}/report/` |
| GET | `/api/automation/reports/summary/` | aggregated report | same as `GET /api/reports/summary/` |

All four require a valid, non-revoked API key; otherwise `401`/`403` with no data (FR-023, US4 AS-5,
AS-6).

---

## Contract test checklist (Phase 2 → tests first)

- [ ] `POST /api/documents/` persists the document + signers before any outbound call (mock gateway
      asserts DB row exists at call time).
- [ ] `POST /api/documents/` returns `201` with `provider_status="failed"` when the ZapSign mock
      raises / times out; document is retrievable afterward.
- [ ] `POST /api/documents/` returns `201` with `latest_analysis.state="failed"` when the AI mock
      fails; `provider_status` still reflects the ZapSign result.
- [ ] `POST /api/documents/{id}/analyze/` inserts a new `DocumentAnalysis`; previous rows unchanged;
      history endpoint returns both, newest first.
- [ ] `DELETE /api/documents/{id}/` removes all its signers and analyses.
- [ ] `DELETE /api/companies/{id}/` with a document ⇒ `409 company_has_documents`.
- [ ] Company responses never contain `api_token`; `api_token` accepted on write.
- [ ] `/api/automation/**` rejects JWT and accepts a valid API key; rejects a revoked key with no
      body data.
- [ ] `/api/health/` returns `200` with DB ok and `503` when the DB check fails; provider failure
      keeps it `200`.
- [ ] Duplicate signer email within one document ⇒ `400` with `fields.email`.
- [ ] Every list mutation response carries the full updated resource (no follow-up GET needed).
