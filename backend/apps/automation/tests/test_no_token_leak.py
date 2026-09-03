"""T090 — the ZapSign credential never appears in an automation response (FR-002)."""

import json

import pytest
from rest_framework.test import APIClient
from rest_framework_api_key.models import APIKey

from apps.companies.tests.factories import CompanyFactory
from apps.documents.tests.factories import DocumentFactory

pytestmark = pytest.mark.django_db

SECRET = "zapsign-super-secret-token-value"


@pytest.fixture
def automation() -> APIClient:
    _, key = APIKey.objects.create_key(name="n8n")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Api-Key {key}")
    return client


def _body(response: object) -> str:
    return json.dumps(getattr(response, "data", None), default=str)


def test_no_automation_response_contains_the_credential_or_a_token_field(
    automation: APIClient,
) -> None:
    company = CompanyFactory.create(api_token=SECRET)
    document = DocumentFactory.create(company=company)
    automation.post(f"/api/automation/documents/{document.pk}/analyze/")

    responses = [
        automation.post(
            "/api/automation/documents/",
            {
                "company": str(company.pk),
                "name": "Via n8n",
                "pdf_url": "https://files.example.test/x.pdf",
                "signers": [{"name": "Bo", "email": "bo@example.com"}],
            },
            format="json",
        ),
        automation.post(f"/api/automation/documents/{document.pk}/analyze/"),
        automation.get(f"/api/automation/documents/{document.pk}/report/"),
        automation.get("/api/automation/reports/summary/"),
    ]

    for response in responses:
        body = _body(response)
        assert SECRET not in body
        assert "api_token" not in body
        assert "api_token_masked" not in body


def test_the_spa_company_endpoint_is_not_reachable_with_an_api_key(
    automation: APIClient,
) -> None:
    CompanyFactory.create(api_token=SECRET)

    response = automation.get("/api/companies/")

    assert response.status_code in {401, 403}
    assert SECRET not in _body(response)
