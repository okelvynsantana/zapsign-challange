"""T031 — deleting an organization that still owns documents is refused (FR-004)."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.companies.models import Company
from apps.companies.tests.factories import CompanyFactory
from apps.documents.tests.factories import DocumentFactory

pytestmark = pytest.mark.django_db


def test_deleting_a_company_with_documents_returns_409(api: APIClient) -> None:
    company = CompanyFactory.create()
    DocumentFactory.create(company=company)

    response = api.delete(f"/api/companies/{company.pk}/")

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data["code"] == "company_has_documents"
    assert Company.objects.filter(pk=company.pk).exists()


def test_the_conflict_explains_the_consequence_rather_than_orphaning(api: APIClient) -> None:
    company = CompanyFactory.create()
    DocumentFactory.create(company=company)

    detail = api.delete(f"/api/companies/{company.pk}/").data["detail"]

    assert "documents" in detail.lower()


def test_deleting_becomes_possible_once_the_documents_are_gone(api: APIClient) -> None:
    company = CompanyFactory.create()
    document = DocumentFactory.create(company=company)
    document.delete()

    response = api.delete(f"/api/companies/{company.pk}/")

    assert response.status_code == status.HTTP_204_NO_CONTENT
