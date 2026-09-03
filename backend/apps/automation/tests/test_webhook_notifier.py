"""T098 — outbound webhook delivery (bonus US6: FR-031, FR-032).

Delivery is best-effort by contract, so most of these assert that nothing escapes.
"""

import hashlib
import hmac
import json
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
import respx

from apps.automation.webhook import (
    HttpWebhookNotifier,
    NullWebhookNotifier,
    WebhookEvent,
)
from apps.integrations.config import WebhookConfig
from apps.integrations.providers import get_webhook_notifier

WEBHOOK_URL = "https://n8n.example.test/webhook/documents"


@pytest.fixture
def event() -> WebhookEvent:
    return WebhookEvent(
        event="document.status_changed",
        occurred_at=datetime(2026, 9, 3, 12, 0, tzinfo=UTC),
        document_id=uuid4(),
        document_name="Contrato X",
        provider_status="submitted",
        signature_status="signed",
        has_risk_insight=True,
        report_url="/api/documents/x/report/",
    )


def _notifier(**overrides: object) -> HttpWebhookNotifier:
    return HttpWebhookNotifier(
        WebhookConfig(url=WEBHOOK_URL, timeout_seconds=1.0, **overrides)  # type: ignore[arg-type]
    )


@respx.mock
def test_the_documented_payload_is_posted_once(event: WebhookEvent) -> None:
    route = respx.post(WEBHOOK_URL).mock(return_value=httpx.Response(200))

    _notifier().notify(event)

    assert route.call_count == 1
    body = json.loads(route.calls.last.request.content)
    assert set(body) == {
        "event",
        "occurred_at",
        "document_id",
        "document_name",
        "provider_status",
        "signature_status",
        "has_risk_insight",
        "report_url",
    }
    assert body["event"] == "document.status_changed"
    assert body["has_risk_insight"] is True
    assert body["document_id"] == str(event.document_id)


@respx.mock
def test_a_connection_error_is_swallowed(event: WebhookEvent) -> None:
    respx.post(WEBHOOK_URL).mock(side_effect=httpx.ConnectError("receiver down"))

    _notifier().notify(event)  # must not raise


@respx.mock
def test_a_timeout_is_swallowed(event: WebhookEvent) -> None:
    respx.post(WEBHOOK_URL).mock(side_effect=httpx.ReadTimeout("too slow"))

    _notifier().notify(event)  # must not raise


@respx.mock
def test_a_500_is_swallowed(event: WebhookEvent) -> None:
    respx.post(WEBHOOK_URL).mock(return_value=httpx.Response(500))

    _notifier().notify(event)  # must not raise


@respx.mock
def test_the_signature_header_is_a_correct_hmac_of_the_raw_body(event: WebhookEvent) -> None:
    route = respx.post(WEBHOOK_URL).mock(return_value=httpx.Response(200))

    _notifier(secret="s3cr3t").notify(event)

    request = route.calls.last.request
    expected = hmac.new(b"s3cr3t", request.content, hashlib.sha256).hexdigest()
    assert request.headers["X-Signature"] == f"sha256={expected}"


@respx.mock
def test_no_signature_header_without_a_secret(event: WebhookEvent) -> None:
    route = respx.post(WEBHOOK_URL).mock(return_value=httpx.Response(200))

    _notifier().notify(event)

    assert "X-Signature" not in route.calls.last.request.headers


def test_the_null_notifier_attempts_no_http(event: WebhookEvent) -> None:
    with respx.mock:
        NullWebhookNotifier().notify(event)
        assert len(respx.calls) == 0


def test_a_blank_url_selects_the_null_notifier(monkeypatch: pytest.MonkeyPatch) -> None:
    from apps.integrations import providers

    monkeypatch.setattr(providers, "_webhook_config", lambda: WebhookConfig(url=""))

    assert isinstance(get_webhook_notifier(), NullWebhookNotifier)


def test_a_configured_url_selects_the_http_notifier(monkeypatch: pytest.MonkeyPatch) -> None:
    from apps.integrations import providers

    monkeypatch.setattr(providers, "_webhook_config", lambda: WebhookConfig(url=WEBHOOK_URL))

    assert isinstance(get_webhook_notifier(), HttpWebhookNotifier)
