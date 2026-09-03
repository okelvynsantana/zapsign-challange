"""`Signer` HTTP surface — thin CRUD over the model."""

from django.db.models import QuerySet
from rest_framework import viewsets

from apps.signers.models import Signer
from apps.signers.serializers import SignerSerializer

__all__ = ["SignerViewSet"]


class SignerViewSet(viewsets.ModelViewSet):
    """Standalone signer management, in addition to nesting inside a document (FR-006)."""

    serializer_class = SignerSerializer
    queryset = Signer.objects.all()

    def get_queryset(self) -> QuerySet[Signer]:
        queryset = Signer.objects.all()
        document_id = self.request.query_params.get("document")
        if document_id:
            queryset = queryset.for_document(document_id)
        return queryset
