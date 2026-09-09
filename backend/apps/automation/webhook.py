"""Outbound event notification to the automation platform (bonus — User Story 6).

Contract: `contracts/webhook-outbound.md`. Delivery is best-effort and MUST NOT affect the
operation that produced the event (FR-032), so `notify` swallows everything: a webhook
receiver being down is the receiver's problem, never the document's.
"""

import hashlib
import hmac
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

import httpx

from apps.integrations.config import WebhookConfig

__all__ = [
    "FakeWebhookNotifier",
    "HttpWebhookNotifier",
    "NullWebhookNotifier",
    "WebhookEvent",
    "WebhookEventName",
    "WebhookNotifier",
    "build_analyzed_event",
    "build_status_changed_event",
]

logger = logging.getLogger("integrations.webhook")

WebhookEventName = Literal["document.status_changed", "document.analyzed"]

SIGNATURE_HEADER = "X-Signature"


@dataclass(frozen=True, slots=True)
class WebhookEvent:
    """The JSON body we POST, exactly as the contract documents it."""

    event: WebhookEventName
    occurred_at: datetime
    document_id: UUID
    document_name: str
    provider_status: str
    signature_status: str | None
    has_risk_insight: bool
    report_url: str

    def as_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["occurred_at"] = self.occurred_at.isoformat()
        payload["document_id"] = str(self.document_id)
        return payload


class WebhookNotifier(ABC):
    """Fire-and-forget event delivery. Implementations MUST NOT raise."""

    @abstractmethod
    def notify(self, event: WebhookEvent) -> None:
        """Deliver `event`. Never raises, whatever the receiver does."""


class NullWebhookNotifier(WebhookNotifier):
    """Selected when no webhook URL is configured — the feature is simply off."""

    def notify(self, event: WebhookEvent) -> None:
        return None


class HttpWebhookNotifier(WebhookNotifier):
    """POSTs the event once, with an optional HMAC signature over the raw body."""

    def __init__(self, config: WebhookConfig) -> None:
        self._config = config

    def notify(self, event: WebhookEvent) -> None:
        body = json.dumps(event.as_payload(), separators=(",", ":")).encode()
        headers = {"Content-Type": "application/json"}
        if self._config.secret:
            headers[SIGNATURE_HEADER] = self._sign(body)

        started = time.perf_counter()
        try:
            response = httpx.post(
                self._config.url,
                content=body,
                headers=headers,
                timeout=self._config.timeout_seconds,
            )
        except Exception as exc:
            self._log(event, outcome="error", started=started, detail=str(exc))
            return

        outcome = "ok" if response.is_success else "error"
        self._log(event, outcome=outcome, started=started, status=response.status_code)

    def _sign(self, body: bytes) -> str:
        digest = hmac.new(self._config.secret.encode(), body, hashlib.sha256).hexdigest()
        return f"sha256={digest}"

    def _log(
        self,
        event: WebhookEvent,
        *,
        outcome: str,
        started: float,
        status: int | None = None,
        detail: str = "",
    ) -> None:
        logger.info(
            "webhook_delivery",
            extra={
                "provider": "webhook",
                "operation": event.event,
                "outcome": outcome,
                "status_code": status,
                "detail": detail,
                "document_id": str(event.document_id),
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )


class FakeWebhookNotifier(WebhookNotifier):
    """Records the events a scenario produced, for assertions."""

    def __init__(self, *, raises: bool = False) -> None:
        self.events: list[WebhookEvent] = []
        self._raises = raises

    def notify(self, event: WebhookEvent) -> None:
        self.events.append(event)
        if self._raises:
            # Contract-breaking on purpose: the service must still survive it.
            raise RuntimeError("notifier exploded")


# -- event builders ------------------------------------------------------------------------


def build_status_changed_event(document: Any) -> WebhookEvent:
    """Emitted when ZapSign reports a different signature status than we held."""
    return _event("document.status_changed", document)


def build_analyzed_event(document: Any) -> WebhookEvent:
    """Emitted when a new analysis row is created."""
    return _event("document.analyzed", document)


def _event(name: WebhookEventName, document: Any) -> WebhookEvent:
    from django.utils import timezone

    # `report_url` is a RELATIVE path by contract: the receiver prefixes whatever base
    # URL reaches us from where it runs. Emitting an absolute URL here breaks that — an
    # n8n workflow that prefixes its own base ends up with two schemes glued together.
    report_url = f"/api/documents/{document.pk}/report/"
    return WebhookEvent(
        event=name,
        occurred_at=timezone.now(),
        document_id=document.pk,
        document_name=document.name,
        provider_status=document.provider_status,
        signature_status=document.status or None,
        has_risk_insight=document.has_open_risk,
        report_url=report_url,
    )
