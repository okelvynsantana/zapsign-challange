"""T045 — the local record survives a ZapSign outage end-to-end (SC-002, Principle IV).

Drives the real HTTP gateway with `respx` standing in for the sandbox, so the resilience
path is exercised through the API exactly as a manager would hit it.
"""

from typing import Any

import httpx
import pytest
import respx
from rest_framework import status
from rest_framework.test import APIClient

from apps.companies.tests.factories import CompanyFactory
from apps.documents.models import Document
from apps.documents.status import ProviderStatus
from apps.integrations.config import ZapSignConfig

pytestmark = pytest.mark.django_db

BASE_URL = "https://sandbox.example.test/api/v1"

SUCCESS_BODY = {
    "open_id": 123456,
    "token": "zapsign-doc-token",
    "status": "pending",
    "external_id": None,
    "signers": [
        {
            "name": "Ana Souza",
            "email": "ana@example.com",
            "token": "signer-token-a",
            "status": "new",
            "external_id": None,
        }
    ],
}


@pytest.fixture(autouse=True)
def _real_gateway(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the gateway factory at a `respx`-mocked sandbox rather than the fake."""
    from apps.integrations import providers

    config = ZapSignConfig(base_url=BASE_URL, timeout_seconds=1.0, use_fake=False)
    monkeypatch.setattr(providers, "_zapsign_config", lambda: config)


def _create(api: APIClient) -> dict[str, Any]:
    return api.post(
        "/api/documents/",
        {
            "company": str(CompanyFactory.create().pk),
            "name": "Contrato X",
            "pdf_url": "https://files.example.test/contrato.pdf",
            "signers": [{"name": "Ana Souza", "email": "ana@example.com"}],
        },
        format="json",
    ).data


@respx.mock
def test_a_provider_outage_still_yields_a_stored_retryable_document(api: APIClient) -> None:
    respx.post(f"{BASE_URL}/docs/").mock(side_effect=httpx.ConnectError("sandbox down"))

    body = _create(api)

    assert body["provider_status"] == ProviderStatus.FAILED
    assert body["last_provider_error"]
    document = Document.objects.get(pk=body["id"])
    assert document.signers.count() == 1


@respx.mock
def test_a_timeout_is_handled_the_same_way(api: APIClient) -> None:
    respx.post(f"{BASE_URL}/docs/").mock(side_effect=httpx.ReadTimeout("too slow"))

    body = _create(api)

    assert body["provider_status"] == ProviderStatus.FAILED
    assert Document.objects.filter(pk=body["id"]).exists()


@respx.mock
def test_resync_recovers_the_document_once_the_provider_is_back(api: APIClient) -> None:
    respx.post(f"{BASE_URL}/docs/").mock(side_effect=httpx.ConnectError("sandbox down"))
    body = _create(api)
    assert body["provider_status"] == ProviderStatus.FAILED

    respx.post(f"{BASE_URL}/docs/").mock(return_value=httpx.Response(200, json=SUCCESS_BODY))
    response = api.post(f"/api/documents/{body['id']}/resync/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["provider_status"] == ProviderStatus.SUBMITTED
    assert response.data["open_id"] == 123456
    assert response.data["token"] == "zapsign-doc-token"


@respx.mock
def test_the_happy_path_stores_the_provider_identifiers(api: APIClient) -> None:
    respx.post(f"{BASE_URL}/docs/").mock(return_value=httpx.Response(200, json=SUCCESS_BODY))

    body = _create(api)

    assert body["provider_status"] == ProviderStatus.SUBMITTED
    assert body["signers"][0]["token"] == "signer-token-a"


@respx.mock
def test_a_provider_auth_failure_is_surfaced_without_leaking_the_credential(
    api: APIClient,
) -> None:
    respx.post(f"{BASE_URL}/docs/").mock(return_value=httpx.Response(401, json={"detail": "nope"}))

    body = _create(api)

    document = Document.objects.get(pk=body["id"])
    assert document.provider_status == ProviderStatus.FAILED
    assert document.company.api_token not in document.last_provider_error
