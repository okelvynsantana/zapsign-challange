# n8n example workflow — document events

Bonus deliverable for **User Story 6** (FR-031, FR-032). See
`specs/001-document-signature-management/contracts/webhook-outbound.md` for the authoritative
contract.

## What the workflow does

`document-events.workflow.json` receives the outbound event our backend emits and, when the document
carries a risk insight, fetches the per-document report and posts a Slack message:

```
Webhook  (POST /webhook/zapsign-document-events)
  └─ IF  has_risk_insight == true
       ├─ true  → HTTP Request  GET {ZAPSIGN_BASE_APP_URL}{report_url}   (Api-Key auth)
       │            → HTTP Request  POST {SLACK_WEBHOOK_URL}   "Risk found in <document_name>"
       └─ false → NoOp  "No risk — ignore"
```

Both events defined in the contract reach this same webhook:

| Change in the system | Emitted event |
|---|---|
| `Document.status` differs from its previous value (after create or `resync`) | `document.status_changed` |
| A new `DocumentAnalysis` is created with `state="succeeded"` and a `risk=true` insight | `document.analyzed` (`has_risk_insight=true`) |
| A new `DocumentAnalysis` with no risk insight | `document.analyzed` (`has_risk_insight=false`) — only when `WEBHOOK_ON_EVERY_ANALYSIS=true` |

The IF node is what separates them in practice: a `document.status_changed` on a document whose
latest analysis has no risk insight takes the false branch and ends at the NoOp.

The Slack step is a plain **HTTP Request** node pointed at a Slack incoming webhook rather than the
built-in Slack node. That is deliberate: it keeps the export free of credential references, so
`Import from File` works on a fresh n8n with nothing to reconnect. Swap it for the Slack (or an
email) node if you prefer managed credentials.

## Event payload

`POST {N8N_WEBHOOK_URL}` · `Content-Type: application/json`

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

In n8n the body lands under `body`, so expressions read `{{ $json.body.has_risk_insight }}`,
`{{ $json.body.document_name }}`, and so on. After the report request the active item is the report
response, so the Slack node reaches back with `$('Webhook').item.json.body.<field>` and reads
`$json.latest_analysis.summary` / `$json.latest_analysis.missing_topics` from the report.

## Import

1. n8n → **Workflows** → **Import from File**.
2. Pick `deploy/n8n/document-events.workflow.json`.
3. Set the three environment variables below, then **Activate** the workflow.
4. Copy the Webhook node's **Production URL** — that is the value for `N8N_WEBHOOK_URL` on our side.

While testing, use the Webhook node's **Test URL** with *Listen for test event* instead; it is only
armed for one request.

## Environment variables the workflow expects

| Variable | Example | Used by |
|---|---|---|
| `ZAPSIGN_BASE_APP_URL` | `http://host.docker.internal:8000` | report + Slack nodes, prefixed to `report_url` |
| `ZAPSIGN_API_KEY` | the plaintext key printed by `create_api_key` | `Authorization: Api-Key <key>` header |
| `SLACK_WEBHOOK_URL` | `https://hooks.slack.com/services/T.../B.../xxx` | Slack notify node |

Set them on the n8n process — e.g. in the n8n service's `environment:` block in Docker Compose, or
in the shell that starts `n8n start`. n8n only exposes `$env` to expressions when access is allowed,
so on self-hosted instances also set `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` (its default permits
access; some hardened images flip it). If you would rather not use `$env`, replace the expressions
with literal values or an n8n *variable*.

Note that `ZAPSIGN_BASE_APP_URL` must be reachable **from the n8n container**, which is not
necessarily `localhost`.

## Pointing the system at n8n

In `deploy/.env`:

```dotenv
N8N_WEBHOOK_URL=https://<n8n-host>/webhook/zapsign-document-events
N8N_WEBHOOK_SECRET=                 # optional; blank = no X-Signature header
```

Leaving `N8N_WEBHOOK_URL` blank turns the feature off entirely (the `NullWebhookNotifier` is
selected and no HTTP is attempted).

### Verifying `X-Signature`

When `N8N_WEBHOOK_SECRET` is set, every POST carries

```
X-Signature: sha256=<hex HMAC-SHA256 of the raw request body, keyed with the secret>
```

The signature covers the **raw bytes** of the body, so verify before any re-serialisation. To check
it in n8n, set the Webhook node's option *Raw body* on and drop a **Code** node right after it:

```javascript
const crypto = require('crypto');

const secret = $env.N8N_WEBHOOK_SECRET;
const raw = $input.first().binary
  ? Buffer.from($input.first().binary.data.data, 'base64')       // raw-body mode
  : Buffer.from(JSON.stringify($input.first().json.body), 'utf8');

const expected = 'sha256=' + crypto.createHmac('sha256', secret).update(raw).digest('hex');
const received = $input.first().json.headers['x-signature'] || '';

const ok =
  expected.length === received.length &&
  crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(received));

if (!ok) {
  throw new Error('Invalid X-Signature — rejecting event');
}

return $input.all();
```

The workflow ships without this node so it imports and runs with no secret configured; add it when
you set `N8N_WEBHOOK_SECRET`.

## Generating the API key

On our side, from `backend/`:

```bash
python manage.py create_api_key "n8n"
```

The plaintext key is printed **once** — copy it straight into `ZAPSIGN_API_KEY` in n8n; it cannot be
recovered later. `python manage.py revoke_api_key <prefix>` revokes it, after which the report
request returns `401`/`403` with no data.

The key authenticates `Authorization: Api-Key <key>` on the report read. The dedicated automation
mirror of the same report lives at `/api/automation/documents/{id}/report/` if you prefer to hit the
API-key-only namespace explicitly — replace the URL expression with
`{{ $env.ZAPSIGN_BASE_APP_URL }}/api/automation/documents/{{ $json.body.document_id }}/report/`.

## Delivery is best-effort

Per FR-032 (and Constitution Principle IV), emission is fire-and-forget **after** the surrounding
transaction commits. A slow, erroring, or entirely unreachable n8n never fails
`POST /api/documents/` or `POST /api/documents/{id}/analyze/` — the exception is caught, logged with
`elapsed_ms` and status, and swallowed. Requests time out after `WEBHOOK_TIMEOUT_SECONDS` (default
`5`). A continuously running n8n instance is therefore not a requirement of the project.

## Screenshot

`screenshot.png` in this directory is a **placeholder** — a blank light-grey canvas, committed only
so the reference resolves. Replace it with a real capture of a successful execution: import and
activate the workflow, point `N8N_WEBHOOK_URL` at it, create or re-analyse a document that yields a
risk insight, then screenshot the n8n **Executions** view showing the green run through
Webhook → IF (true) → Fetch document report → Notify Slack. Keep the same filename.
