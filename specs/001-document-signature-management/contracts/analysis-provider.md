# Contract: Analysis Provider & Pipeline (internal interface)

**Feature**: `001-document-signature-management` | **App**: `apps/integrations/analysis` + `.../pdf`

Domain and application code depend on these **abstract interfaces**, never on the `openai` SDK,
`pypdf`, or HTTP directly (Constitution Principle I / PRD RNF09). This isolation is what lets the
provider be swapped and lets a future move to asynchronous processing change only the caller
(PRD §10.2).

---

## 1. `PdfTextExtractor` (abstract)

```python
class PdfTextExtractor(ABC):
    @abstractmethod
    def extract(self, pdf_url: str) -> str: ...      # returns extracted plain text
```

- Implementation `PypdfTextExtractor`: fetches `pdf_url` with a bounded timeout
  (`PDF_FETCH_TIMEOUT_SECONDS`, default 10) and a max size guard (`PDF_MAX_BYTES`, default 20 MiB),
  then extracts text with `pypdf`.
- Raises `PdfExtractionError`:

  ```python
  class PdfExtractionError(Exception):
      kind: Literal["unreachable", "not_pdf", "too_large", "no_text", "timeout"]
      message: str
  ```

  `no_text` is raised when the PDF parses but yields only whitespace (scanned/image-only) — spec
  treats this as "no extractable text".
- `FakePdfTextExtractor` (tests): returns queued text or raises a queued `PdfExtractionError`.

---

## 2. `AnalysisProvider` (abstract)

```python
class AnalysisProvider(ABC):
    @abstractmethod
    def analyze(self, document_text: str) -> ProviderAnalysis: ...
```

- Synchronous; MUST complete within `AI_TIMEOUT_SECONDS` (default 15) or raise
  `AnalysisProviderError(kind="timeout")`.
- Implementation `OpenAIAnalysisProvider`: one direct call to the OpenAI Chat Completions API
  (`AI_MODEL`, default `gpt-4o-mini`) requesting a strict JSON object. No LangChain.
- Error model:

  ```python
  class AnalysisProviderError(Exception):
      kind: Literal["timeout", "connection", "rate_limit", "http_status", "invalid_response", "auth"]
      status_code: int | None
      message: str
  ```

Typed result of the provider call:

```python
@dataclass(frozen=True)
class ProviderAnalysis:
    summary: str
    missing_topics: list[str]
    insights: list[Insight]        # Insight(text: str, risk: bool)
    model: str
```

### Prompt / response contract (OpenAI implementation)

- System prompt (pt-BR): instructs the model that it reviews Brazilian contracts and MUST return
  **only** a JSON object with keys `summary` (string, pt-BR), `missing_topics` (array of strings —
  expected contract clauses that appear absent), `insights` (array of `{text, risk}` where `risk`
  is true for anything that could harm the contracting party).
- User message: the extracted document text, truncated to `AI_MAX_INPUT_CHARS` (default 60000) with
  a note when truncated.
- `response_format` requests a JSON object; the implementation validates the parsed shape and raises
  `AnalysisProviderError(kind="invalid_response")` if keys/types are wrong.
- `FakeAnalysisProvider` (tests): returns a queued `ProviderAnalysis` or raises a queued
  `AnalysisProviderError`; records the text it was given.

---

## 3. `AnalysisPipeline` (application service in `apps/integrations/analysis/pipeline.py`)

Orchestrates extraction → LLM → regex reinforcement → typed result. This is what
`DocumentService.analyze` calls. It **does not** touch the database; it returns an `AnalysisResult`
that the caller persists as a `DocumentAnalysis` row.

```python
class AnalysisPipeline:
    def __init__(self, extractor: PdfTextExtractor, provider: AnalysisProvider,
                 clause_checker: ClauseChecker) -> None: ...

    def run(self, pdf_url: str) -> AnalysisResult: ...
```

`AnalysisResult` (domain dataclass, `documents/domain/entities.py`):

```python
@dataclass(frozen=True)
class AnalysisResult:
    state: Literal["succeeded", "failed"]
    summary: str
    missing_topics: list[str]
    insights: list[Insight]
    source: Literal["llm", "regex", "llm+regex"]
    model: str | None
    error_reason: str        # "" when succeeded
```

### Pipeline rules

1. `extractor.extract(pdf_url)`.
   - `PdfExtractionError` → return `AnalysisResult(state="failed", error_reason=<kind>, source="regex",
     summary="", missing_topics=[], insights=[], model=None)`. (No LLM call attempted.)
2. `provider.analyze(text)`.
   - Success → base result from `ProviderAnalysis`, `source="llm"`, `model=<model>`.
   - `AnalysisProviderError` → **fallback**: run `clause_checker` on the extracted text only and
     return `AnalysisResult(state="succeeded", summary="", missing_topics=<regex hits>, insights=[],
     source="regex", model=None, error_reason="")` **only if** `AI_REGEX_FALLBACK_ENABLED` (default
     true). If disabled → `AnalysisResult(state="failed", error_reason="provider_<kind>",
     source="regex")`.
3. `clause_checker.missing_clauses(text)` → merge into `missing_topics` (dedupe, preserve order).
   If the LLM succeeded and the checker added at least one clause → `source="llm+regex"`.
4. Final `state` is `succeeded` when step 2 produced model output (or the regex fallback was taken);
   `failed` otherwise.

### `ClauseChecker` (`apps/integrations/analysis/clause_checker.py`)

```python
class ClauseChecker:
    def __init__(self, clauses: Mapping[str, Sequence[str]]) -> None: ...  # label -> keyword/regex list
    def missing_clauses(self, text: str) -> list[str]: ...                 # labels whose patterns are absent
```

Default clause set (config-overridable, `AI_EXPECTED_CLAUSES`): `objeto`, `prazo/vigência`,
`rescisão`, `multa/penalidade`, `foro`, `confidencialidade`, `pagamento`, `proteção de dados/LGPD`.

---

## 4. How the service persists the result (`apps/documents/services.py`)

`DocumentService.analyze(document_id)`:

- Loads the `Document` (404 if gone).
- `result = pipeline.run(document.pdf_url)`.
- Inserts a new `DocumentAnalysis` from `result` (never updates an existing one — FR-017).
- Returns the new row. Failures here never touch `Document.provider_status` (FR-020).

On `POST /api/documents/` the same call is made once after the ZapSign step; its failure does not
fail the `201`.

---

## Behavioural contract (test list — write first, TDD)

Pipeline (`AnalysisPipeline.run` with fakes):

- [ ] Extractor `no_text` → `state="failed"`, `error_reason="no_text"`, no provider call made.
- [ ] Extractor `unreachable` → `state="failed"`, `error_reason="unreachable"`.
- [ ] Provider success + checker finds nothing → `source="llm"`, `state="succeeded"`, summary passed
      through.
- [ ] Provider success + checker adds `foro` → `source="llm+regex"`, `foro` in `missing_topics`
      exactly once even if the LLM also listed it.
- [ ] Provider `timeout` + fallback enabled → `state="succeeded"`, `source="regex"`, `summary=""`,
      `missing_topics` = checker output, `model=None`.
- [ ] Provider `timeout` + fallback disabled → `state="failed"`, `error_reason="provider_timeout"`.
- [ ] Provider returns `insights` with a `risk=true` item → preserved in `AnalysisResult.insights`.

Service (`DocumentService.analyze` with a fake pipeline + real DB):

- [ ] Creates exactly one new `DocumentAnalysis`; a pre-existing analysis row is untouched.
- [ ] A `failed` pipeline result still creates a `DocumentAnalysis(state="failed")` and does not
      change `Document.provider_status`.
- [ ] `GET /api/documents/{id}/` then returns the newest analysis as `latest_analysis`.

OpenAI provider (`OpenAIAnalysisProvider` with the SDK/HTTP mocked):

- [ ] Sends the extracted text and parses a well-formed JSON object into `ProviderAnalysis`.
- [ ] Malformed JSON / missing keys → `AnalysisProviderError(kind="invalid_response")`.
- [ ] Simulated timeout → `AnalysisProviderError(kind="timeout")` (not a raw SDK error).
- [ ] 401 → `AnalysisProviderError(kind="auth")`. No API key value in logs/exception text.

---

## Configuration (`apps/integrations/config.py`, typed, env-driven)

| Setting | Env var | Default |
|---|---|---|
| model | `AI_MODEL` | `gpt-4o-mini` |
| API key | `OPENAI_API_KEY` | — (required for the real provider) |
| call timeout (s) | `AI_TIMEOUT_SECONDS` | `15` |
| max input chars | `AI_MAX_INPUT_CHARS` | `60000` |
| regex fallback | `AI_REGEX_FALLBACK_ENABLED` | `true` |
| expected clauses | `AI_EXPECTED_CLAUSES` | built-in pt-BR set |
| PDF fetch timeout (s) | `PDF_FETCH_TIMEOUT_SECONDS` | `10` |
| PDF max bytes | `PDF_MAX_BYTES` | `20971520` |
