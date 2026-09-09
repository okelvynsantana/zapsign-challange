"""Reusable `Document` query logic (plan.md: the `QuerySet` is the query abstraction)."""

from datetime import timedelta
from uuid import UUID

from django.db.models import OuterRef, Prefetch, Q, QuerySet, Subquery
from django.utils import timezone

__all__ = ["TERMINAL_SIGNATURE_STATUSES", "DocumentQuerySet"]

#: Signature statuses that end a document's life: it can no longer be "stalled".
#: The vocabulary is ZapSign's, so this is a best-effort mapping, not a closed enum.
TERMINAL_SIGNATURE_STATUSES: frozenset[str] = frozenset({"signed", "refused", "cancelled"})


class DocumentQuerySet(QuerySet["Document"]):  # type: ignore[name-defined]
    """Query helpers shared by the viewset, the automation surface and the reports."""

    def for_company(self, company_id: object) -> "DocumentQuerySet":
        return self.filter(company_id=company_id)

    def by_provider_status(self, provider_status: str) -> "DocumentQuerySet":
        return self.filter(provider_status=provider_status)

    def by_signature_status(self, signature_status: str) -> "DocumentQuerySet":
        return self.filter(status=signature_status)

    def with_signers(self) -> "DocumentQuerySet":
        """Prefetch signers so a list render is two queries, not one per document."""
        return self.prefetch_related("signers")

    def with_latest_analysis(self) -> "DocumentQuerySet":
        """Prefetch each document's analyses newest-first, so `latest_analysis` is free."""
        from apps.documents.models import DocumentAnalysis

        return self.prefetch_related(
            Prefetch("analyses", queryset=DocumentAnalysis.objects.order_by("-created_at"))
        )

    def stalled(self, threshold_days: int) -> "DocumentQuerySet":
        """Documents still awaiting signature past the configured threshold (FR-030)."""
        cutoff = timezone.now() - timedelta(days=threshold_days)
        return self.filter(created_at__lt=cutoff).exclude(Q(status__in=TERMINAL_SIGNATURE_STATUSES))

    def latest_analysis_ids(self) -> list[UUID]:
        """The id of each document's newest analysis (one subquery, no N+1)."""
        from apps.documents.models import DocumentAnalysis

        newest = Subquery(
            DocumentAnalysis.objects.filter(document=OuterRef("pk"))
            .order_by("-created_at")
            .values("pk")[:1]
        )
        return [
            analysis_id
            for analysis_id in self.annotate(_latest_id=newest).values_list("_latest_id", flat=True)
            if analysis_id is not None
        ]

    def with_open_risk(self) -> "DocumentQuerySet":
        """Only documents whose *latest* analysis succeeded and flagged a risk.

        The `risk` flag lives inside a JSON array, and JSON containment lookups are not
        portable across our backends (PostgreSQL in production, SQLite for a bare-clone
        test run). So the newest analysis per document is resolved in SQL and the flag is
        evaluated in Python — two extra queries, bounded by the number of documents, which
        is well within this system's scale (plan.md: hundreds to low thousands).
        """
        from apps.documents.models import DocumentAnalysis

        risky = [
            analysis.document_id
            for analysis in DocumentAnalysis.objects.filter(
                pk__in=self.latest_analysis_ids(),
                state=DocumentAnalysis.State.SUCCEEDED,
            )
            if analysis.has_risk_insight
        ]
        return self.filter(pk__in=risky)
