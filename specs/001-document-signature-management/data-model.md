# Phase 1 Data Model: Document & Signature Management System

**Feature**: `001-document-signature-management` | **Date**: 2026-09-03

Derived from `spec.md` (Key Entities, Functional Requirements) and `PRD.md` §8. Conventions:

- Every domain entity has a **UUID v4 primary key** (`id`), server-generated, non-editable
  (Constitution Principle VI, PRD RNF14).
- All timestamps are timezone-aware UTC. `created_at` set on insert; `last_updated_at` /
  `updated_at` set on every save.
- Persistence is **PostgreSQL**; all schema changes ship as Django migrations (PRD RNF06).
- Each entity is mirrored by a **frozen, fully typed dataclass** in the owning app's `domain/`
  package (`entities.py`) that carries the pure business rules; the Django model is the persistence
  adapter only.
- Fields returned by ZapSign (`open_id`, `token`, `external_id`) are **their** identifiers and have
  no relationship to our primary keys.

---

## Entity: Company  *(app: `companies`)*

Represents the organization on whose behalf documents are sent for signature. One row in normal use;
the table is retained so multiple organizations/credentials are possible later (PRD §8 note).

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK, default uuid4, not editable | |
| `name` | string(255) | required, non-empty (trimmed) | display name |
| `api_token` | string(255) | required | ZapSign account API token. **Write-only**; never serialized back in full; never exposed on any `automation` endpoint (FR-002). Stored via a `SecretString` value object; encrypted at rest if `FIELD_ENCRYPTION_KEY` is set, otherwise plain column with a documented warning. |
| `created_at` | datetime | auto, insert | |
| `last_updated_at` | datetime | auto, every save | PRD §8 name |

**Relationships**: `Company` 1 ── N `Document` (`Document.company`, `on_delete=PROTECT`).

**Validation rules**:

- `name` MUST be non-empty after trimming (FR-001).
- `api_token` MUST be present on create (FR-001); on update, an omitted/blank `api_token` keeps the
  existing value (so editing the name never wipes the credential).
- Delete is **rejected** while any `Document` references the company (`PROTECT`); the API returns
  `409 Conflict` with an explanatory message (FR-004). The SPA surfaces this as a confirmation-style
  error.

**Domain dataclass** (`companies/domain/entities.py`): `Company(id: UUID, name: str, api_token:
SecretString, created_at: datetime, last_updated_at: datetime)` with `masked_token() -> str` and
`with_updated_name(name: str) -> "Company"`.

---

## Entity: Document  *(app: `documents`)*

A file to be signed. Persisted locally **before** any external call (FR-008, Principle IV).

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK, default uuid4, not editable | our identifier |
| `company` | FK → Company | required, `on_delete=PROTECT` | owning organization (FR-003) |
| `name` | string(255) | required, non-empty | document name (FR-007) |
| `pdf_url` | URL string(2048) | required, `http`/`https`, validated | source of content for analysis & ZapSign |
| `provider_status` | enum `ProviderStatus` | required, default `pending_integration` | **our** lifecycle for the ZapSign hand-off; drives retry (FR-010) |
| `open_id` | integer | nullable | returned by ZapSign (FR-009) |
| `token` | string(255) | nullable, blank | returned by ZapSign (FR-009) |
| `external_id` | string(255) | nullable, blank | optional caller-supplied external reference |
| `status` | string(64) | nullable, blank | **signature** status as reported by ZapSign (e.g. `pending`, `signed`, `refused`); free-text mirror of provider value (FR-013) |
| `created_by` | string(255) | nullable, blank | username / API-key name that created it |
| `last_provider_error` | text | nullable, blank | reason captured on the last failed ZapSign attempt |
| `created_at` | datetime | auto, insert | |
| `last_updated_at` | datetime | auto, every save | |

**Relationships**:

- `Document` N ── 1 `Company`.
- `Document` 1 ── N `Signer` (`Signer.document`, `on_delete=CASCADE`) — deleting a document deletes
  its signers (FR-011, SC-005).
- `Document` 1 ── N `DocumentAnalysis` (`DocumentAnalysis.document`, `on_delete=CASCADE`),
  **append-only**; the "current" analysis is the one with the greatest `created_at` (FR-017,
  FR-018).

**`ProviderStatus` enum & transitions** (`documents/domain/status.py`):

```
pending_integration ──(ZapSign create OK)──▶ submitted
pending_integration ──(ZapSign error/timeout)──▶ failed
failed ──(POST /documents/{id}/resync/)──▶ pending_integration ──▶ submitted | failed
submitted ──(POST /documents/{id}/resync/ to refresh)──▶ submitted   (status/signature refreshed)
```

- Only `failed` and `submitted` accept a `resync` trigger; `pending_integration` while an attempt is
  in flight is not re-triggerable (guarded in the service).
- Transition logic lives in the domain layer as pure typed functions; the model stores the string.

**Signature `status`**: opaque string owned by ZapSign; the system stores and displays it and never
computes signature outcomes itself.

**Validation rules**:

- `name` non-empty; `pdf_url` required and URL-valid (FR-005, FR-007).
- On create via any surface, **at least one signer** must be provided (FR-007); enforced in
  `DocumentService.create`, not the model, so the document+signers are written in one transaction.
- `company` must reference an existing `Company` (FR-003).
- `open_id` / `token` / `status` are only written by the service from a ZapSign response or a
  `resync`, never by client input.

**Domain dataclass** (`documents/domain/entities.py`): `Document(...)` fully typed, with
`can_resync() -> bool`, `mark_submitted(result: ZapSignDocumentResult) -> "Document"`,
`mark_provider_failed(reason: str) -> "Document"`.

---

## Entity: Signer  *(app: `signers`)*

A person expected to sign a document.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK, default uuid4, not editable | |
| `document` | FK → Document | required, `on_delete=CASCADE` | (FR-011) |
| `name` | string(255) | required, non-empty | (FR-006, FR-007) |
| `email` | email string(320) | required, RFC-valid | (FR-006, FR-007) |
| `token` | string(255) | nullable, blank | per-signer token from ZapSign |
| `status` | string(64) | nullable, blank | per-signer signature status from ZapSign |
| `external_id` | string(255) | nullable, blank | optional external reference |

**Relationships**: `Signer` N ── 1 `Document`.

**Validation rules**:

- `name` non-empty; `email` must pass email validation (FR-006).
- **Duplicate-email policy** (edge case): the same `email` MUST NOT appear twice on the **same**
  document — enforced by a `UniqueConstraint(fields=["document", "email"])`; the API returns
  `400` with a field error. The same email on different documents is allowed.
- `token` / `status` are written only by the service from ZapSign data.

**Domain dataclass** (`signers/domain/entities.py`): `Signer(id: UUID, document_id: UUID, name: str,
email: str, token: str | None, status: str | None, external_id: str | None)` with
`normalized_email() -> str`.

---

## Entity: DocumentAnalysis  *(app: `documents`)*

The outcome of analyzing a document's content at a point in time. **Insert-only** — a new row per
analysis run; earlier rows are never mutated or deleted except by document cascade (FR-017).

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK, default uuid4, not editable | |
| `document` | FK → Document | required, `on_delete=CASCADE` | |
| `state` | enum `AnalysisState` | required | `succeeded` \| `failed` (FR-019) |
| `summary` | text | required if `state=succeeded`, else blank | plain-language summary (FR-014) |
| `missing_topics` | JSON (array of string) | default `[]` | expected-but-absent clauses (FR-014) |
| `insights` | JSON (array of object) | default `[]` | each: `{ "text": str, "risk": bool }` (FR-014); `risk=true` marks a risk insight (bonus FR-030/031) |
| `source` | enum `AnalysisSource` | required | `llm` \| `regex` \| `llm+regex` (FR-021, PRD §10.2) |
| `error_reason` | string(255) | required if `state=failed`, else blank | e.g. `provider_timeout`, `provider_error`, `pdf_unreachable`, `no_extractable_text` (FR-019) |
| `model` | string(128) | nullable, blank | LLM model id used, when `source` includes `llm` |
| `created_at` | datetime | auto, insert | ordering key for "current" |

**Relationships**: `DocumentAnalysis` N ── 1 `Document`.

**`AnalysisState` transitions**: none. A row is created already `succeeded` or `failed` and is
immutable. "Retry" = create a new row (FR-019). "Current" = `ORDER BY created_at DESC LIMIT 1`.

**Derived helper**: `Document.latest_analysis` (property / annotated queryset) and
`Document.has_open_risk` = latest analysis is `succeeded` and any `insights[*].risk` is true.

**Validation rules**:

- `state=succeeded` ⇒ `summary` non-empty, `error_reason` blank.
- `state=failed` ⇒ `error_reason` non-empty; `summary`/`missing_topics`/`insights` may be empty.
- `missing_topics` entries are non-empty strings; `insights` entries match the object shape above.

**Domain dataclass** (`documents/domain/entities.py`): `AnalysisResult(summary: str, missing_topics:
list[str], insights: list[Insight], source: AnalysisSource, model: str | None)` and
`Insight(text: str, risk: bool)` — produced by the analysis pipeline, persisted into a
`DocumentAnalysis`.

---

## Entity: AutomationCredential  *(app: `automation`)*

A revocable API key issued to an external automation consumer (n8n). Backed by
`djangorestframework-api-key`'s `APIKey` model (or a thin subclass), listed here for completeness.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` / `prefix` | string | PK / lookup prefix | library-managed |
| `name` | string(100) | required | which integration this key is for |
| `hashed_key` | string | required | library-managed; full key shown **once** at creation (FR-024) |
| `revoked` | boolean | default false | revoking blocks all future calls (FR-023, US4-6) |
| `created` | datetime | auto | |
| `expiry_date` | datetime | nullable | optional |

**Validation / behavior rules**:

- The plaintext key is returned only in the creation response and never again.
- Auth resolves a request key by `prefix`, verifies the hash, and rejects if missing, malformed,
  `revoked`, or past `expiry_date` (FR-023) → `401`/`403`, no body data.
- Not exposed through the SPA in this feature; created via Django admin / management command.

---

## Derived (non-persisted) view: Alert  *(app: `automation` or `documents`; bonus)*

Computed on request for the alerts dashboard (US5). Not a table.

| Field | Type | Notes |
|---|---|---|
| `type` | enum | `stalled` \| `risk` |
| `document_id` | UUID | the document the alert concerns |
| `document_name` | string | for display |
| `detail` | string | e.g. `"pending 9 days"` or the risk insight text |
| `since` | datetime | `document.created_at` (stalled) or latest analysis `created_at` (risk) |

**Rules**:

- `stalled`: `provider_status != submitted-and-signed` equivalent — concretely, `status` not in a
  terminal signed set **and** `now - created_at > ALERT_STALLED_DAYS` (config, default 5).
- `risk`: `Document.has_open_risk` is true (latest analysis `succeeded`, an insight has `risk=true`).
- Empty result set renders an empty state, never an error (US5 AS-3).

---

## Cross-entity integrity summary

| Rule | Mechanism | Requirement |
|---|---|---|
| Delete Document ⇒ delete its Signers | FK `on_delete=CASCADE` | FR-011, SC-005 |
| Delete Document ⇒ delete its Analyses | FK `on_delete=CASCADE` | FR-017 (history is per-document) |
| Delete Company with Documents ⇒ blocked | FK `on_delete=PROTECT` → `409` | FR-004 |
| Document always has a Company | FK `null=False` | FR-003 |
| Document created before any external call | single transaction in `DocumentService.create` | FR-008, Principle IV |
| Analyses never overwritten | insert-only; no update path in service or serializer | FR-017 |
| ZapSign `api_token` never leaves the system | write-only serializer field; absent from all `automation` responses | FR-002 |
| One email per signer per document | `UniqueConstraint(document, email)` | edge case |

## Indexes (initial)

- `Document(company_id)`, `Document(provider_status)`, `Document(created_at)`
- `Signer(document_id)`, unique `Signer(document_id, email)`
- `DocumentAnalysis(document_id, created_at DESC)` — supports "latest analysis" and history
