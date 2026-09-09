"""T113 — structured logging and secret redaction (Constitution Principle V, FR-029).

Two guarantees are worth a regression test: one structured entry per request and per
external call carrying status and elapsed time, and no credential ever reaching a log line.
"""

import json
import logging

import pytest
from rest_framework.test import APIClient

from apps.companies.tests.factories import CompanyFactory
from apps.core.logging import JsonFormatter, log_gateway_call, redact

pytestmark = pytest.mark.django_db


def extra(record: logging.LogRecord, field: str) -> object:
    """Read a field attached via `extra=`; these are invisible to `LogRecord`'s type."""
    return getattr(record, field)


# -- per-request logging -------------------------------------------------------------------


def test_each_request_logs_one_entry_with_status_and_timing(
    api: APIClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="api.request"):
        api.get("/api/documents/")

    (record,) = [r for r in caplog.records if r.name == "api.request"]
    assert extra(record, "method") == "GET"
    assert extra(record, "path") == "/api/documents/"
    assert extra(record, "status_code") == 200
    assert extra(record, "elapsed_ms") >= 0  # type: ignore[operator]


def test_the_correlation_id_is_echoed_back_and_honoured(api: APIClient) -> None:
    response = api.get("/api/documents/", HTTP_X_CORRELATION_ID="trace-123")

    assert response["X-Correlation-ID"] == "trace-123"


def test_the_access_log_record_carries_the_correlation_id(
    api: APIClient, caplog: pytest.LogCaptureFixture
) -> None:
    # Losing it here would defeat the point of having one (FR-029).
    with caplog.at_level(logging.INFO, logger="api.request"):
        api.get("/api/documents/", HTTP_X_CORRELATION_ID="trace-123")

    (record,) = [r for r in caplog.records if r.name == "api.request"]
    assert extra(record, "correlation_id") == "trace-123"


def test_a_generated_correlation_id_is_used_when_the_caller_sends_none(
    api: APIClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="api.request"):
        response = api.get("/api/documents/")

    (record,) = [r for r in caplog.records if r.name == "api.request"]
    generated = extra(record, "correlation_id")
    assert generated not in ("", "-", None)
    assert response["X-Correlation-ID"] == generated


def test_work_logged_during_a_request_shares_its_correlation_id(
    api: APIClient, caplog: pytest.LogCaptureFixture
) -> None:
    from apps.core.logging import CorrelationIdFilter

    records: list[logging.LogRecord] = []

    class Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            CorrelationIdFilter().filter(record)
            records.append(record)

    handler = Capture()
    logging.getLogger("api.request").addHandler(handler)
    try:
        api.get("/api/documents/", HTTP_X_CORRELATION_ID="trace-xyz")
    finally:
        logging.getLogger("api.request").removeHandler(handler)

    assert [getattr(r, "correlation_id", None) for r in records] == ["trace-xyz"]


def test_a_failing_request_is_still_logged_with_its_status(
    anonymous_api: APIClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="api.request"):
        anonymous_api.get("/api/documents/")

    (record,) = [r for r in caplog.records if r.name == "api.request"]
    assert extra(record, "status_code") == 401


# -- per-gateway-call logging ---------------------------------------------------------------


def test_a_successful_gateway_call_logs_provider_operation_and_timing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    @log_gateway_call(provider="zapsign", operation="create_document")
    def call() -> str:
        return "ok"

    with caplog.at_level(logging.INFO, logger="integrations.gateway"):
        call()

    (record,) = caplog.records
    assert (
        extra(record, "provider"),
        extra(record, "operation"),
        extra(record, "outcome"),
    ) == ("zapsign", "create_document", "ok")
    assert extra(record, "elapsed_ms") >= 0  # type: ignore[operator]


def test_a_failing_gateway_call_logs_the_failure_and_re_raises(
    caplog: pytest.LogCaptureFixture,
) -> None:
    @log_gateway_call(provider="openai", operation="analyze")
    def call() -> None:
        raise RuntimeError("boom")

    with (
        caplog.at_level(logging.WARNING, logger="integrations.gateway"),
        pytest.raises(RuntimeError),
    ):
        call()

    (record,) = caplog.records
    assert extra(record, "outcome") == "error"
    assert extra(record, "error_class") == "RuntimeError"
    assert extra(record, "elapsed_ms") >= 0  # type: ignore[operator]


# -- redaction --------------------------------------------------------------------------------


def test_redact_removes_a_secret_from_free_text() -> None:
    secret = "s3cret-token-value"
    assert secret not in redact(f"token {secret} denied", [secret])


def test_redact_ignores_values_too_short_to_be_credentials() -> None:
    # Redacting a 1-2 character string would mangle unrelated text.
    assert redact("a and b", ["a"]) == "a and b"


def test_no_credential_appears_in_the_logs_of_a_full_request(
    api: APIClient, caplog: pytest.LogCaptureFixture
) -> None:
    secret = "zapsign-super-secret-token-value"
    company = CompanyFactory.create(api_token=secret)

    with caplog.at_level(logging.DEBUG):
        api.post(
            "/api/documents/",
            {
                "company": str(company.pk),
                "name": "Contrato X",
                "pdf_url": "https://files.example.test/x.pdf",
                "signers": [{"name": "Ana", "email": "ana@example.com"}],
            },
            format="json",
        )
        api.get(f"/api/companies/{company.pk}/")

    assert secret not in caplog.text


def test_the_json_formatter_emits_a_parseable_envelope() -> None:
    formatter = JsonFormatter("%(timestamp)s %(level)s %(logger)s %(message)s")
    record = logging.LogRecord("api.request", logging.INFO, __file__, 1, "request", None, None)
    record.correlation_id = "abc"

    payload = json.loads(formatter.format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "api.request"
    assert payload["correlation_id"] == "abc"
