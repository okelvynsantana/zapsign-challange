"""Derived alerts for the operations dashboard (bonus — User Story 5).

Nothing here is persisted: an alert is a *view* over documents and their latest analysis,
computed per request (data-model.md "Derived view: Alert"). That keeps it always accurate
and spares us any invalidation logic.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from django.conf import settings

from apps.documents.models import Document

__all__ = ["Alert", "AlertType", "build_alerts"]

AlertType = Literal["stalled", "risk"]


@dataclass(frozen=True, slots=True)
class Alert:
    """One item on the dashboard."""

    type: AlertType
    document_id: UUID
    document_name: str
    detail: str
    since: datetime


def build_alerts(*, stalled_days: int | None = None) -> list[Alert]:
    """Every document needing attention, newest first.

    Two independent conditions (FR-030): a document has been pending too long, or its
    latest analysis flagged a risk. A document can raise both, and does so as two alerts —
    they are different problems with different fixes.

    An empty result is a legitimate answer, never an error (US5 AS-3).
    """
    threshold = stalled_days if stalled_days is not None else settings.ALERT_STALLED_DAYS

    alerts = [*_stalled_alerts(threshold), *_risk_alerts()]
    return sorted(alerts, key=lambda alert: alert.since, reverse=True)


def _stalled_alerts(threshold_days: int) -> list[Alert]:
    return [
        Alert(
            type="stalled",
            document_id=document.pk,
            document_name=document.name,
            detail=f"pending {_days_since(document.created_at)} days",
            since=document.created_at,
        )
        for document in Document.objects.all().stalled(threshold_days)
    ]


def _risk_alerts() -> list[Alert]:
    alerts: list[Alert] = []
    for document in Document.objects.all().with_open_risk().with_latest_analysis():
        latest = document.latest_analysis
        if latest is None:
            continue
        for insight in latest.risk_insights:
            alerts.append(
                Alert(
                    type="risk",
                    document_id=document.pk,
                    document_name=document.name,
                    detail=str(insight.get("text", "")),
                    since=latest.created_at,
                )
            )
    return alerts


def _days_since(moment: datetime) -> int:
    from django.utils import timezone

    return (timezone.now() - moment).days
