"""Reusable `Company` query logic (plan.md: query logic lives in `querysets.py`)."""

from django.db.models import Count, QuerySet

__all__ = ["CompanyQuerySet"]


class CompanyQuerySet(QuerySet["Company"]):  # type: ignore[name-defined]
    """Query helpers shared by the viewset, the reports and the admin."""

    def with_document_count(self) -> "CompanyQuerySet":
        """Annotate `document_count` so callers can show/guard deletion without an N+1."""
        return self.annotate(document_count=Count("documents"))

    def deletable(self) -> "CompanyQuerySet":
        """Only companies no document references (deleting any other is blocked by PROTECT)."""
        return self.with_document_count().filter(document_count=0)
