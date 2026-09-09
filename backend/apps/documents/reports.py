"""Report aggregation for the SPA and for automation consumers (FR-025, FR-026).

Computed live from the ORM on every request: at this system's scale a direct aggregate is
well inside the latency budget, and a materialised store would need invalidation logic
that nothing here justifies (research.md §15, Constitution Principle III).
"""

from typing import Any

from django.db.models import Count
from django.utils import timezone

from apps.documents.models import Document, DocumentAnalysis
from apps.documents.status import ProviderStatus

__all__ = ["RECENT_RISK_INSIGHT_LIMIT", "document_report", "summary_report"]

#: How many risk insights the aggregated report carries.
RECENT_RISK_INSIGHT_LIMIT = 10

#: Signature status is ZapSign's, and it is blank until they report one.
UNKNOWN_SIGNATURE_STATUS = "unknown"


def document_report(document: Document) -> dict[str, Any]:
    """The per-document report: current status plus the most recent analysis (FR-025)."""
    return {
        "document_id": document.pk,
        "name": document.name,
        "provider_status": document.provider_status,
        "signature_status": document.status or None,
        "signers": list(document.signers.all()),
        "latest_analysis": document.latest_analysis,
        "created_at": document.created_at,
        "last_updated_at": document.last_updated_at,
    }


def summary_report() -> dict[str, Any]:
    """The aggregated report across all documents (FR-026).

    An empty database yields a well-formed summary of zeros rather than an error — the
    automation consumer should not have to special-case a fresh install (spec edge case).
    """
    documents = Document.objects.all()
    latest_analyses = _latest_analyses(documents)

    risky = [analysis for analysis in latest_analyses if analysis.has_risk_insight]

    return {
        "total_documents": documents.count(),
        "by_provider_status": _by_provider_status(documents),
        "by_signature_status": _by_signature_status(documents),
        "documents_with_risk_insight": len(risky),
        "recent_risk_insights": _recent_risk_insights(risky),
        "generated_at": timezone.now(),
    }


# -- internals ---------------------------------------------------------------------------


def _by_provider_status(documents: Any) -> dict[str, int]:
    """Every `ProviderStatus` is present, so a consumer can read a zero without a KeyError."""
    counts = dict.fromkeys(ProviderStatus.values, 0)
    for row in documents.values("provider_status").annotate(total=Count("pk")):
        counts[row["provider_status"]] = row["total"]
    return counts


def _by_signature_status(documents: Any) -> dict[str, int]:
    """Only the statuses actually seen: the vocabulary belongs to ZapSign, not to us."""
    counts: dict[str, int] = {}
    for row in documents.values("status").annotate(total=Count("pk")):
        counts[row["status"] or UNKNOWN_SIGNATURE_STATUS] = row["total"]
    return counts


def _latest_analyses(documents: Any) -> list[DocumentAnalysis]:
    """Each document's newest analysis, resolved in one query."""
    return list(
        DocumentAnalysis.objects.filter(pk__in=documents.latest_analysis_ids()).select_related(
            "document"
        )
    )


def _recent_risk_insights(risky: list[DocumentAnalysis]) -> list[dict[str, Any]]:
    """The most recent risk-flagged insights, newest analysis first."""
    insights: list[dict[str, Any]] = []
    for analysis in sorted(risky, key=lambda a: a.created_at, reverse=True):
        for insight in analysis.risk_insights:
            insights.append(
                {
                    "document_id": analysis.document_id,
                    "name": analysis.document.name,
                    "text": insight.get("text", ""),
                    "created_at": analysis.created_at,
                }
            )
            if len(insights) >= RECENT_RISK_INSIGHT_LIMIT:
                return insights
    return insights
