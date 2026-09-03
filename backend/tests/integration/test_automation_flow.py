"""T084 — an automation consumer's whole journey on one issued key (SC-007, US4)."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_api_key.models import APIKey

from apps.companies.tests.factories import CompanyFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def automation() -> APIClient:
    _, key = APIKey.objects.create_key(name="n8n")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Api-Key {key}")
    return client


def test_create_analyze_and_pull_both_reports_with_only_a_key(automation: APIClient) -> None:
    company = CompanyFactory.create()

    created = automation.post(
        "/api/automation/documents/",
        {
            "company": str(company.pk),
            "name": "Contrato via automação",
            "pdf_url": "https://files.example.test/contrato.pdf",
            "signers": [{"name": "Bo", "email": "bo@example.com"}],
        },
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
    document_id = created.data["id"]

    analyzed = automation.post(f"/api/automation/documents/{document_id}/analyze/")
    assert analyzed.status_code == status.HTTP_201_CREATED

    report = automation.get(f"/api/automation/documents/{document_id}/report/")
    assert report.status_code == status.HTTP_200_OK
    assert report.data["name"] == "Contrato via automação"
    assert report.data["latest_analysis"]["id"] == analyzed.data["id"]

    summary = automation.get("/api/automation/reports/summary/")
    assert summary.status_code == status.HTTP_200_OK
    assert summary.data["total_documents"] == 1
    assert summary.data["by_provider_status"]["submitted"] == 1


def test_the_summary_reflects_a_risk_insight_raised_by_the_analysis(
    automation: APIClient,
) -> None:
    company = CompanyFactory.create()
    automation.post(
        "/api/automation/documents/",
        {
            "company": str(company.pk),
            "name": "Contrato com risco",
            "pdf_url": "https://files.example.test/contrato.pdf",
            "signers": [{"name": "Bo", "email": "bo@example.com"}],
        },
        format="json",
    )

    summary = automation.get("/api/automation/reports/summary/").data

    # The fake analysis provider flags one risk insight (see FakeAnalysisProvider).
    assert summary["documents_with_risk_insight"] == 1
    assert summary["recent_risk_insights"][0]["name"] == "Contrato com risco"


def test_the_whole_journey_is_closed_off_once_the_key_is_revoked(
    automation: APIClient,
) -> None:
    company = CompanyFactory.create()
    created = automation.post(
        "/api/automation/documents/",
        {
            "company": str(company.pk),
            "name": "Antes da revogação",
            "pdf_url": "https://files.example.test/contrato.pdf",
            "signers": [{"name": "Bo", "email": "bo@example.com"}],
        },
        format="json",
    )
    document_id = created.data["id"]

    key = APIKey.objects.get(name="n8n")
    key.revoked = True
    key.save()

    assert automation.get("/api/automation/reports/summary/").status_code == 403
    assert automation.get(f"/api/automation/documents/{document_id}/report/").status_code == 403
    assert automation.post(f"/api/automation/documents/{document_id}/analyze/").status_code == 403
