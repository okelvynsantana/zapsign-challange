"""`Company` HTTP surface — a thin viewset over the model (plan.md architecture stance)."""

from django.db.models import ProtectedError, QuerySet
from rest_framework import viewsets

from apps.companies.models import Company
from apps.companies.serializers import CompanySerializer
from apps.core.exceptions import ConflictError

__all__ = ["CompanyViewSet"]


class CompanyViewSet(viewsets.ModelViewSet):
    """CRUD for the organization profile (FR-001 … FR-004)."""

    serializer_class = CompanySerializer
    queryset = Company.objects.all()

    def get_queryset(self) -> QuerySet[Company]:
        return Company.objects.all().order_by("name")

    def perform_destroy(self, instance: Company) -> None:
        try:
            instance.delete()
        except ProtectedError as exc:
            # FR-004: never silently orphan documents; explain the consequence instead.
            raise ConflictError(
                detail=(
                    "This organization still has documents. Delete or reassign them "
                    "before deleting the organization."
                ),
                code="company_has_documents",
            ) from exc
