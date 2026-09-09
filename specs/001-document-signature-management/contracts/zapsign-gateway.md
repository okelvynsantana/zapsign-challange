# Contract: ZapSign Gateway (internal interface)

**Feature**: `001-document-signature-management` | **App**: `apps/integrations/zapsign`

The domain and application layers depend on this **abstract interface**, never on `httpx`, the
ZapSign SDK, or ZapSign URLs directly (Constitution Principle I / PRD RNF09). Two implementations
exist: `HttpZapSignGateway` (real, `httpx`) and `FakeZapSignGateway` (tests / local offline).

## Interface

```python
class ZapSignGateway(ABC):
    @abstractmethod
    def create_document(self, request: ZapSignCreateRequest) -> ZapSignCreateResult: ...

    @abstractmethod
    def get_document(self, *, api_token: str, doc_token: str) -> ZapSignDocumentStatus: ...
```

All methods are **synchronous** and MUST complete within the configured connect/read timeouts
(`ZAPSIGN_TIMEOUT_SECONDS`, default 10). On any failure they raise `ZapSignError` (see below) — they
never return partial/ambiguous results and never raise raw `httpx` exceptions.

## Typed data structures

```python
@dataclass(frozen=True)
class ZapSignSignerInput:
    name: str
    email: str

@dataclass(frozen=True)
class ZapSignCreateRequest:
    api_token: str            # the owning Company.api_token — passed in, never read from global config
    name: str
    pdf_url: str
    signers: tuple[ZapSignSignerInput, ...]
    external_id: str | None = None

@dataclass(frozen=True)
class ZapSignSignerResult:
    name: str
    email: str
    token: str | None
    status: str | None
    external_id: str | None

@dataclass(frozen=True)
class ZapSignCreateResult:
    open_id: int
    token: str
    status: str                       # signature status as reported by ZapSign
    external_id: str | None
    signers: tuple[ZapSignSignerResult, ...]

@dataclass(frozen=True)
class ZapSignDocumentStatus:
    open_id: int
    token: str
    status: str
    signers: tuple[ZapSignSignerResult, ...]
```

## Error model

```python
class ZapSignError(Exception):
    kind: Literal["timeout", "connection", "http_status", "invalid_response", "auth"]
    status_code: int | None      # set when kind == "http_status" | "auth"
    message: str                 # safe to log; never contains api_token
```

- `timeout` / `connection` → transient; `Document.provider_status` becomes `failed`, retry via
  `POST /api/documents/{id}/resync/`.
- `auth` (401/403 from ZapSign) → the stored `Company.api_token` is wrong; surfaced in
  `last_provider_error`, still retryable after the token is fixed.
- `http_status` (4xx/5xx) / `invalid_response` (unparseable body) → `failed`, retryable.
- The gateway MUST redact `api_token` from every log line and exception message.

## Mapping to our model (done in `apps.documents.services`, not the gateway)

| ZapSign field | Our field |
|---|---|
| `ZapSignCreateResult.open_id` | `Document.open_id` |
| `ZapSignCreateResult.token` | `Document.token` |
| `ZapSignCreateResult.status` | `Document.status` |
| `ZapSignSignerResult.token` / `.status` matched by email | `Signer.token` / `Signer.status` |
| success | `Document.provider_status = "submitted"`, `last_provider_error = ""` |
| `ZapSignError` | `Document.provider_status = "failed"`, `last_provider_error = error.message` |

## Behavioural contract (test list — write these first, TDD)

Against `HttpZapSignGateway` with `respx`-mocked HTTP:

- [ ] `create_document` issues one POST to the configured sandbox base URL with `api_token` in the
      documented auth position and a body containing name, `url_pdf`, and signer name/email pairs.
- [ ] A 200 response is parsed into `ZapSignCreateResult` with `open_id`, `token`, `status`, and
      per-signer tokens.
- [ ] A read timeout raises `ZapSignError(kind="timeout")` — not `httpx.ReadTimeout`.
- [ ] A 401 raises `ZapSignError(kind="auth", status_code=401)`.
- [ ] A 500 raises `ZapSignError(kind="http_status", status_code=500)`.
- [ ] A 200 with a malformed body raises `ZapSignError(kind="invalid_response")`.
- [ ] No log line or exception string contains the `api_token` value.
- [ ] `get_document` returns `ZapSignDocumentStatus` and maps signer statuses.

`FakeZapSignGateway` (used by the document service tests) supports: queued success result, queued
`ZapSignError`, and records the last `ZapSignCreateRequest` it received.

## Configuration (`apps/integrations/config.py`, typed, env-driven)

| Setting | Env var | Default |
|---|---|---|
| base URL | `ZAPSIGN_BASE_URL` | `https://sandbox.api.zapsign.com.br/api/v1` |
| timeout (s) | `ZAPSIGN_TIMEOUT_SECONDS` | `10` |
| verify TLS | `ZAPSIGN_VERIFY_SSL` | `true` |

The `api_token` is **not** configuration — it is always taken from the `Company` row for the
document being created.
