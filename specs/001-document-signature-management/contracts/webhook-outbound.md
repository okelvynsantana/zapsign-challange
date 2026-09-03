# Contract: Outbound Automation Webhook  *(bonus — User Story 6)*

**Feature**: `001-document-signature-management` | **App**: `apps/automation/webhook.py`

The system POSTs an event to a configured external endpoint (`N8N_WEBHOOK_URL`) when a document's
signature status changes or an analysis completes with a risk insight (FR-031). Delivery is
best-effort and MUST NOT affect the originating operation (FR-032, Constitution Principle IV).

## Interface

```python
class WebhookNotifier(ABC):
    @abstractmethod
    def notify(self, event: WebhookEvent) -> None: ...   # never raises to the caller
```

- `HttpWebhookNotifier`: one POST with `httpx`, timeout `WEBHOOK_TIMEOUT_SECONDS` (default 5). Any
  exception or non-2xx is caught, logged (structured, with `elapsed_ms` and status), and swallowed.
- `NullWebhookNotifier`: used when `N8N_WEBHOOK_URL` is unset (feature effectively off).
- `FakeWebhookNotifier`: records events for tests.

## Event payload

`POST {N8N_WEBHOOK_URL}`  ·  `Content-Type: application/json`  ·  header
`X-Signature: sha256=<hmac>` when `N8N_WEBHOOK_SECRET` is set (HMAC-SHA256 of the raw body).

```json
{
  "event": "document.status_changed | document.analyzed",
  "occurred_at": "2026-09-03T12:00:00Z",
  "document_id": "uuid",
  "document_name": "Contrato X",
  "provider_status": "submitted",
  "signature_status": "signed",
  "has_risk_insight": true,
  "report_url": "/api/documents/uuid/report/"
}
```

| Field | Type | Notes |
|---|---|---|
| `event` | enum | `document.status_changed` (signature status transitioned) or `document.analyzed` (a new analysis row was created) |
| `occurred_at` | ISO-8601 UTC | when the triggering change was committed |
| `document_id` / `document_name` | string | identify the document |
| `provider_status` | enum | our `ProviderStatus` at emit time |
| `signature_status` | string \| null | ZapSign status at emit time |
| `has_risk_insight` | boolean | latest analysis is `succeeded` and any `insights[*].risk` is true |
| `report_url` | string | relative path to the per-document report |

## Trigger points (in `DocumentService`, after the DB commit)

| Change | Emitted event |
|---|---|
| `Document.status` differs from its previous value (after create or `resync`) | `document.status_changed` |
| A new `DocumentAnalysis` row is created with `state="succeeded"` and a `risk=true` insight | `document.analyzed` (`has_risk_insight=true`) |
| A new `DocumentAnalysis` with no risk insight | `document.analyzed` (`has_risk_insight=false`) — sent only if `WEBHOOK_ON_EVERY_ANALYSIS` (default false) |

Emission is a fire-and-forget call to `WebhookNotifier.notify(...)` made **after** the surrounding
transaction commits, so a webhook failure cannot roll back the document/analysis.

## Example n8n workflow (delivered artifact)

`deploy/n8n/document-events.workflow.json` (exported) implementing:

```
Webhook (receives our event)
  → IF has_risk_insight == true
      → HTTP Request  GET {BASE_URL}{report_url}   (Api-Key auth)
      → Slack / Email  "Risk found in {document_name}"
```

Delivered as the exported JSON plus a screenshot of a successful run (`deploy/n8n/screenshot.png`);
a continuously running n8n instance is not required (spec Assumptions).

## Behavioural contract (test list — write first, TDD)

- [ ] `HttpWebhookNotifier.notify` POSTs the documented JSON to `N8N_WEBHOOK_URL` once.
- [ ] A connection error / timeout / 500 from the endpoint is swallowed — `notify` returns `None`,
      no exception propagates.
- [ ] With `N8N_WEBHOOK_SECRET` set, the `X-Signature` header is a correct HMAC-SHA256 of the body.
- [ ] `NullWebhookNotifier` is selected when `N8N_WEBHOOK_URL` is empty; no HTTP attempted.
- [ ] `DocumentService.create` with a `FakeWebhookNotifier`: a status change emits exactly one
      `document.status_changed`; a risk-bearing analysis emits one `document.analyzed` with
      `has_risk_insight=true`.
- [ ] A `FakeWebhookNotifier` that raises inside `notify` still does not fail
      `POST /api/documents/` (defensive: the notifier contract says it must not raise, but the
      service guards anyway).

## Configuration

| Setting | Env var | Default |
|---|---|---|
| target URL | `N8N_WEBHOOK_URL` | — (unset ⇒ feature off) |
| signing secret | `N8N_WEBHOOK_SECRET` | — (unset ⇒ no `X-Signature`) |
| timeout (s) | `WEBHOOK_TIMEOUT_SECONDS` | `5` |
| emit on every analysis | `WEBHOOK_ON_EVERY_ANALYSIS` | `false` |
| public base URL for `report_url` consumers | `PUBLIC_BASE_URL` | `http://localhost:8000` |
