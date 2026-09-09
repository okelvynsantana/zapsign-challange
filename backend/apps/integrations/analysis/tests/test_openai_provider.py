"""T064 — `OpenAIAnalysisProvider` (contracts/analysis-provider.md §2).

The OpenAI SDK v3 talks over its own vendored HTTP stack, so `respx` cannot intercept it.
Instead the SDK client is injected and made to return real `ChatCompletion` models or
raise the SDK's real exception types — which is what the mapping under test consumes. No
call leaves the process (Constitution Principle II).
"""

import json
import logging
from typing import Any

import httpx2
import openai
import pytest
from openai.types.chat import ChatCompletion

from apps.integrations.analysis.openai_provider import OpenAIAnalysisProvider
from apps.integrations.analysis.provider import AnalysisProviderError
from apps.integrations.config import AnalysisConfig

API_KEY = "sk-test-secret-key-value"
REQUEST = httpx2.Request("POST", "https://api.openai.com/v1/chat/completions")

WELL_FORMED = {
    "summary": "Contrato de prestação de serviços com vigência de 12 meses.",
    "missing_topics": ["foro", "confidencialidade"],
    "insights": [
        {"text": "Multa de 50% é desproporcional.", "risk": True},
        {"text": "Prazo de pagamento é claro.", "risk": False},
    ],
}


def _completion(content: object) -> ChatCompletion:
    body = content if isinstance(content, str) else json.dumps(content)
    return ChatCompletion.model_validate(
        {
            "id": "chatcmpl-1",
            "object": "chat.completion",
            "created": 0,
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": body},
                    "finish_reason": "stop",
                }
            ],
        }
    )


class StubClient:
    """Stands in for `openai.OpenAI`, exposing just `chat.completions.create`."""

    def __init__(self, outcome: ChatCompletion | Exception) -> None:
        self._outcome = outcome
        self.calls: list[dict[str, Any]] = []
        self.chat = type("Chat", (), {"completions": self})()

    def create(self, **kwargs: Any) -> ChatCompletion:
        self.calls.append(kwargs)
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return self._outcome


def _provider(
    outcome: ChatCompletion | Exception, **config: Any
) -> tuple[OpenAIAnalysisProvider, StubClient]:
    client = StubClient(outcome)
    settings = AnalysisConfig(api_key=API_KEY, model="gpt-4o-mini", timeout_seconds=1.0, **config)
    # `StubClient` implements only the `chat.completions.create` surface the provider
    # uses; it is deliberately not an `openai.OpenAI`.
    return OpenAIAnalysisProvider(settings, client=client), client  # type: ignore[arg-type]


def test_a_well_formed_response_is_parsed() -> None:
    provider, _ = _provider(_completion(WELL_FORMED))

    result = provider.analyze("CONTRATO DE PRESTAÇÃO DE SERVIÇOS")

    assert result.summary.startswith("Contrato")
    assert result.missing_topics == ["foro", "confidencialidade"]
    assert [i.risk for i in result.insights] == [True, False]
    assert result.insights[0].text.startswith("Multa")
    assert result.model == "gpt-4o-mini"


def test_the_document_text_and_model_are_what_get_sent() -> None:
    provider, client = _provider(_completion(WELL_FORMED))

    provider.analyze("CLÁUSULA PRIMEIRA — DO OBJETO")

    (call,) = client.calls
    assert call["model"] == "gpt-4o-mini"
    assert call["response_format"] == {"type": "json_object"}
    assert any("CLÁUSULA PRIMEIRA" in m["content"] for m in call["messages"])


def test_long_input_is_truncated_to_the_configured_budget() -> None:
    provider, client = _provider(_completion(WELL_FORMED), max_input_chars=100)

    provider.analyze("x" * 5000)

    user_message = client.calls[0]["messages"][-1]["content"]
    assert len(user_message) < 5000
    assert "truncado" in user_message


def test_malformed_json_raises_invalid_response() -> None:
    provider, _ = _provider(_completion("not json at all"))

    with pytest.raises(AnalysisProviderError) as exc_info:
        provider.analyze("texto")

    assert exc_info.value.kind == "invalid_response"


def test_missing_keys_raise_invalid_response() -> None:
    provider, _ = _provider(_completion({"summary": "só isso"}))

    with pytest.raises(AnalysisProviderError) as exc_info:
        provider.analyze("texto")

    assert exc_info.value.kind == "invalid_response"


def test_a_wrongly_typed_field_raises_invalid_response() -> None:
    provider, _ = _provider(
        _completion({"summary": "ok", "missing_topics": "foro", "insights": []})
    )

    with pytest.raises(AnalysisProviderError) as exc_info:
        provider.analyze("texto")

    assert exc_info.value.kind == "invalid_response"


def test_a_timeout_raises_a_typed_timeout() -> None:
    provider, _ = _provider(openai.APITimeoutError(request=REQUEST))

    with pytest.raises(AnalysisProviderError) as exc_info:
        provider.analyze("texto")

    assert exc_info.value.kind == "timeout"


def test_a_connection_failure_raises_a_typed_connection_error() -> None:
    provider, _ = _provider(openai.APIConnectionError(request=REQUEST))

    with pytest.raises(AnalysisProviderError) as exc_info:
        provider.analyze("texto")

    assert exc_info.value.kind == "connection"


def test_a_401_raises_auth() -> None:
    provider, _ = _provider(
        openai.AuthenticationError(
            "invalid key", response=httpx2.Response(401, request=REQUEST), body=None
        )
    )

    with pytest.raises(AnalysisProviderError) as exc_info:
        provider.analyze("texto")

    assert exc_info.value.kind == "auth"
    assert exc_info.value.status_code == 401


def test_a_429_raises_rate_limit() -> None:
    provider, _ = _provider(
        openai.RateLimitError(
            "slow down", response=httpx2.Response(429, request=REQUEST), body=None
        )
    )

    with pytest.raises(AnalysisProviderError) as exc_info:
        provider.analyze("texto")

    assert exc_info.value.kind == "rate_limit"


def test_a_500_raises_http_status() -> None:
    provider, _ = _provider(
        openai.InternalServerError(
            "boom", response=httpx2.Response(500, request=REQUEST), body=None
        )
    )

    with pytest.raises(AnalysisProviderError) as exc_info:
        provider.analyze("texto")

    assert exc_info.value.kind == "http_status"
    assert exc_info.value.status_code == 500


def test_the_api_key_never_reaches_a_log_line_or_an_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider, _ = _provider(
        openai.AuthenticationError(
            f"key {API_KEY} invalid",
            response=httpx2.Response(401, request=REQUEST),
            body=None,
        )
    )

    with caplog.at_level(logging.DEBUG), pytest.raises(AnalysisProviderError) as exc_info:
        provider.analyze("texto")

    assert API_KEY not in str(exc_info.value)
    assert API_KEY not in exc_info.value.message
    assert API_KEY not in caplog.text
