"""T083 — the automation namespace (US4: FR-022, FR-023, AS-1 … AS-6)."""

from typing import Any

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_api_key.models import APIKey

from apps.companies.tests.factories import CompanyFactory
from apps.documents.models import Document
from apps.documents.tests.factories import DocumentFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def key() -> str:
    _, key = APIKey.objects.create_key(name="n8n")
    return key


@pytest.fixture
def automation(key: str) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Api-Key {key}")
    return client


def _payload() -> dict[str, Any]:
    return {
        "company": str(CompanyFactory.create().pk),
        "name": "Via n8n",
        "pdf_url": "https://files.example.test/x.pdf",
        "signers": [{"name": "Bo", "email": "bo@example.com"}],
    }


# -- happy paths -------------------------------------------------------------------------


def test_a_document_can_be_created_with_a_key(automation: APIClient) -> None:
    response = automation.post("/api/automation/documents/", _payload(), format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert Document.objects.filter(pk=response.data["id"]).exists()


def test_the_creating_key_is_recorded_as_the_author(automation: APIClient) -> None:
    response = automation.post("/api/automation/documents/", _payload(), format="json")

    assert Document.objects.get(pk=response.data["id"]).created_by == "n8n"


def test_creation_runs_the_same_submission_and_analysis_as_the_manual_flow(
    automation: APIClient,
) -> None:
    response = automation.post("/api/automation/documents/", _payload(), format="json")

    assert response.data["provider_status"] == "submitted"
    assert response.data["latest_analysis"]["state"] == "succeeded"


def test_a_fresh_analysis_can_be_triggered(automation: APIClient) -> None:
    document = DocumentFactory.create()

    response = automation.post(f"/api/automation/documents/{document.pk}/analyze/")

    assert response.status_code == status.HTTP_201_CREATED
    assert document.analyses.count() == 1


def test_the_per_document_report_carries_status_and_latest_analysis(
    automation: APIClient,
) -> None:
    document = DocumentFactory.create(status="pending")
    automation.post(f"/api/automation/documents/{document.pk}/analyze/")

    response = automation.get(f"/api/automation/documents/{document.pk}/report/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["signature_status"] == "pending"
    assert response.data["latest_analysis"]["state"] == "succeeded"


def test_the_summary_report_is_reachable(automation: APIClient) -> None:
    DocumentFactory.create()

    response = automation.get("/api/automation/reports/summary/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["total_documents"] == 1
    assert "by_provider_status" in response.data


def test_the_summary_is_well_formed_with_no_documents(automation: APIClient) -> None:
    response = automation.get("/api/automation/reports/summary/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["total_documents"] == 0
    assert response.data["recent_risk_insights"] == []


# -- credential rejection ----------------------------------------------------------------

ENDPOINTS = [
    ("post", "/api/automation/documents/"),
    ("get", "/api/automation/reports/summary/"),
]


@pytest.mark.parametrize(("method", "url"), ENDPOINTS)
def test_no_credential_is_rejected_with_no_data(method: str, url: str) -> None:
    response = getattr(APIClient(), method)(url)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert set(response.data) == {"detail", "code"}


@pytest.mark.parametrize(("method", "url"), ENDPOINTS)
def test_a_jwt_is_rejected_on_the_automation_namespace(
    method: str, url: str, api: APIClient
) -> None:
    # `api` carries a valid SPA JWT — which is not a credential for this namespace.
    response = getattr(api, method)(url)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "id" not in response.data


@pytest.mark.parametrize(("method", "url"), ENDPOINTS)
def test_a_malformed_key_is_rejected(method: str, url: str) -> None:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Api-Key totally-made-up")

    assert getattr(client, method)(url).status_code == status.HTTP_401_UNAUTHORIZED


def test_a_revoked_key_stops_working(key: str) -> None:
    document = DocumentFactory.create()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Api-Key {key}")
    assert client.get("/api/automation/reports/summary/").status_code == status.HTTP_200_OK

    api_key = APIKey.objects.get(name="n8n")
    api_key.revoked = True
    api_key.save()

    for response in (
        client.get("/api/automation/reports/summary/"),
        client.get(f"/api/automation/documents/{document.pk}/report/"),
        client.post(f"/api/automation/documents/{document.pk}/analyze/"),
        client.post("/api/automation/documents/", _payload(), format="json"),
    ):
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert set(response.data) == {"detail", "code"}


def test_an_invalid_payload_still_validates_the_same_way(automation: APIClient) -> None:
    response = automation.post(
        "/api/automation/documents/",
        {**_payload(), "signers": []},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "signers" in response.data["fields"]
