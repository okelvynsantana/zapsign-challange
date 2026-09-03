"""T085 — the shared report reads accept either credential (contracts/rest-api.md)."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_api_key.models import APIKey

from apps.documents.tests.factories import DocumentFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def keyed_client() -> APIClient:
    _, key = APIKey.objects.create_key(name="n8n")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Api-Key {key}")
    return client


def test_the_document_report_accepts_a_jwt(api: APIClient) -> None:
    document = DocumentFactory.create()

    response = api.get(f"/api/documents/{document.pk}/report/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["document_id"] == str(document.pk)


def test_the_document_report_accepts_an_api_key(keyed_client: APIClient) -> None:
    document = DocumentFactory.create()

    response = keyed_client.get(f"/api/documents/{document.pk}/report/")

    assert response.status_code == status.HTTP_200_OK


def test_the_summary_report_accepts_a_jwt(api: APIClient) -> None:
    assert api.get("/api/reports/summary/").status_code == status.HTTP_200_OK


def test_the_summary_report_accepts_an_api_key(keyed_client: APIClient) -> None:
    assert keyed_client.get("/api/reports/summary/").status_code == status.HTTP_200_OK


def test_the_shared_reports_reject_an_anonymous_caller(anonymous_api: APIClient) -> None:
    document = DocumentFactory.create()

    assert anonymous_api.get("/api/reports/summary/").status_code == 401
    assert anonymous_api.get(f"/api/documents/{document.pk}/report/").status_code == 401


def test_the_shared_reports_reject_a_revoked_key() -> None:
    api_key, key = APIKey.objects.create_key(name="retired")
    api_key.revoked = True
    api_key.save()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Api-Key {key}")

    response = client.get("/api/reports/summary/")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "total_documents" not in response.data
