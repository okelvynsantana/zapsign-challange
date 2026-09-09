"""Direct OpenAI implementation of `AnalysisProvider` (research.md §4, no LangChain).

One call, a strict JSON response schema, and every SDK failure mapped onto
`AnalysisProviderError`. Retries are disabled: the whole analysis runs inside the user's
request under a 15 s budget (SC-003), so silently retrying would blow it.
"""

import json
from typing import Any

import openai

from apps.core.logging import log_gateway_call, redact
from apps.integrations.analysis.provider import (
    AnalysisProvider,
    AnalysisProviderError,
    ProviderAnalysis,
)
from apps.integrations.analysis.results import Insight
from apps.integrations.config import AnalysisConfig

__all__ = ["SYSTEM_PROMPT", "OpenAIAnalysisProvider"]

HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_TOO_MANY_REQUESTS = 429

TRUNCATION_NOTE = "\n\n[Texto truncado por limite de tamanho.]"

SYSTEM_PROMPT = """\
Você revisa contratos brasileiros. Analise o texto fornecido e responda SOMENTE com um \
objeto JSON, sem texto adicional, com exatamente estas chaves:

- "summary": string em português do Brasil, resumo em linguagem simples do contrato.
- "missing_topics": array de strings — cláusulas que se esperaria encontrar e que parecem \
ausentes (por exemplo: rescisão, foro, vigência, confidencialidade, multa, pagamento, \
proteção de dados).
- "insights": array de objetos {"text": string, "risk": booleano} — observações úteis; \
"risk" deve ser true para qualquer ponto que possa prejudicar a parte contratante.
"""


class OpenAIAnalysisProvider(AnalysisProvider):
    """Calls the OpenAI Chat Completions API once and validates the shape it returns."""

    def __init__(
        self,
        config: AnalysisConfig,
        base_url: str | None = None,
        client: openai.OpenAI | None = None,
    ) -> None:
        self._config = config
        self._client = client or openai.OpenAI(
            api_key=config.api_key or "unset",
            base_url=base_url,
            timeout=config.timeout_seconds,
            max_retries=0,
        )

    @log_gateway_call(provider="openai", operation="analyze")
    def analyze(self, document_text: str) -> ProviderAnalysis:
        try:
            completion = self._client.chat.completions.create(
                model=self._config.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": self._truncate(document_text)},
                ],
                response_format={"type": "json_object"},
                timeout=self._config.timeout_seconds,
            )
        except openai.APITimeoutError as exc:
            raise self._error("timeout", str(exc)) from exc
        except openai.APIStatusError as exc:
            raise self._from_status(exc) from exc
        except openai.APIConnectionError as exc:
            raise self._error("connection", str(exc)) from exc
        except openai.OpenAIError as exc:
            raise self._error("http_status", str(exc)) from exc

        return self._parse(completion.choices[0].message.content or "")

    # -- internals ---------------------------------------------------------------------

    def _truncate(self, text: str) -> str:
        limit = self._config.max_input_chars
        if len(text) <= limit:
            return text
        return text[:limit] + TRUNCATION_NOTE

    def _from_status(self, exc: openai.APIStatusError) -> AnalysisProviderError:
        status_code = exc.status_code
        if status_code in (HTTP_UNAUTHORIZED, HTTP_FORBIDDEN):
            kind = "auth"
        elif status_code == HTTP_TOO_MANY_REQUESTS:
            kind = "rate_limit"
        else:
            kind = "http_status"
        return self._error(kind, str(exc), status_code=status_code)

    def _parse(self, content: str) -> ProviderAnalysis:
        try:
            payload = json.loads(content)
        except (json.JSONDecodeError, TypeError) as exc:
            raise self._error("invalid_response", f"The model did not return JSON: {exc}") from exc

        if not isinstance(payload, dict):
            raise self._error("invalid_response", "The model returned a non-object body.")

        summary = payload.get("summary")
        missing = payload.get("missing_topics")
        insights = payload.get("insights")

        if (
            not isinstance(summary, str)
            or not isinstance(missing, list)
            or not isinstance(insights, list)
        ):
            raise self._error(
                "invalid_response",
                "The model's JSON is missing a required key or has the wrong type.",
            )

        return ProviderAnalysis(
            summary=summary,
            missing_topics=[str(topic) for topic in missing if str(topic).strip()],
            insights=[self._insight(item) for item in insights if isinstance(item, dict)],
            model=self._config.model,
        )

    @staticmethod
    def _insight(item: dict[str, Any]) -> Insight:
        return Insight(text=str(item.get("text", "")), risk=bool(item.get("risk", False)))

    def _error(
        self, kind: str, message: str, status_code: int | None = None
    ) -> AnalysisProviderError:
        # The key can appear in an SDK error string; never let it travel further.
        safe = redact(message, [self._config.api_key])
        return AnalysisProviderError(kind, safe, status_code=status_code)  # type: ignore[arg-type]
