"""Reusable `Signer` query logic."""

from django.db.models import QuerySet

__all__ = ["SignerQuerySet"]


class SignerQuerySet(QuerySet["Signer"]):  # type: ignore[name-defined]
    """Query helpers for the signers surface."""

    def for_document(self, document_id: object) -> "SignerQuerySet":
        return self.filter(document_id=document_id)
