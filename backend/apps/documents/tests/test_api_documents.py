"""T043 — `/api/documents/` surface (US2: FR-005 … FR-013, contracts/rest-api.md)."""

from typing import Any

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.companies.tests.factories import CompanyFactory
from apps.documents.models import Document
from apps.documents.status import ProviderStatus
from apps.documents.tests.factories import DocumentFactory
from apps.signers.models import Signer
from apps.signers.tests.factories import SignerFactory

pytestmark = pytest.mark.django_db

ENDPOINT = "/api/documents/"


def _payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "company": str(CompanyFactory.create().pk),
        "name": "Contrato de Prestação de Serviços",
        "pdf_url": "https://files.example.test/contrato.pdf",
        "signers": [{"name": "Ana Souza", "email": "ana@example.com"}],
    }
    payload.update(overrides)
    return payload


def test_create_returns_201_with_the_document_and_its_signers(api: APIClient) -> None:
    response = api.post(ENDPOINT, _payload(), format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["name"] == "Contrato de Prestação de Serviços"
    assert [s["email"] for s in response.data["signers"]] == ["ana@example.com"]
    assert response.data["provider_status"] in {
        ProviderStatus.SUBMITTED,
        ProviderStatus.FAILED,
        ProviderStatus.PENDING_INTEGRATION,
    }


def test_create_requires_at_least_one_signer(api: APIClient) -> None:
    response = api.post(ENDPOINT, _payload(signers=[]), format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "signers" in response.data["fields"]


def test_create_rejects_an_unknown_company(api: APIClient) -> None:
    response = api.post(
        ENDPOINT,
        _payload(company="00000000-0000-4000-8000-000000000000"),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "company" in response.data["fields"]


def test_create_rejects_a_duplicate_signer_email_in_the_payload(api: APIClient) -> None:
    response = api.post(
        ENDPOINT,
        _payload(
            signers=[
                {"name": "Ana", "email": "ana@example.com"},
                {"name": "Ana again", "email": "ana@example.com"},
            ]
        ),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "signers" in str(response.data["fields"])


def test_create_rejects_an_invalid_pdf_url(api: APIClient) -> None:
    response = api.post(ENDPOINT, _payload(pdf_url="not-a-url"), format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "pdf_url" in response.data["fields"]


def test_provider_fields_are_read_only_on_write(api: APIClient) -> None:
    response = api.post(
        ENDPOINT,
        _payload(provider_status="submitted", open_id=999, token="forged", status="signed"),
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    document = Document.objects.get(pk=response.data["id"])
    assert document.token != "forged"


def test_list_reflects_created_documents(api: APIClient) -> None:
    DocumentFactory.create_batch(2)

    response = api.get(ENDPOINT)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2


def test_list_can_be_filtered_by_provider_status(api: APIClient) -> None:
    DocumentFactory.create(provider_status=ProviderStatus.FAILED)
    DocumentFactory.create(provider_status=ProviderStatus.SUBMITTED)

    response = api.get(ENDPOINT, {"provider_status": "failed"})

    assert response.data["count"] == 1
    assert response.data["results"][0]["provider_status"] == "failed"


def test_patch_updates_the_editable_fields(api: APIClient) -> None:
    document = DocumentFactory.create()

    response = api.patch(
        f"{ENDPOINT}{document.pk}/",
        {"name": "Contrato revisado", "pdf_url": "https://files.example.test/v2.pdf"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    document.refresh_from_db()
    assert document.name == "Contrato revisado"
    assert document.pdf_url == "https://files.example.test/v2.pdf"


def test_patch_can_replace_the_signer_list(api: APIClient) -> None:
    document = DocumentFactory.create()
    SignerFactory.create(document=document, email="old@example.com")

    response = api.patch(
        f"{ENDPOINT}{document.pk}/",
        {"signers": [{"name": "Nova", "email": "nova@example.com"}]},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert [s.email for s in document.signers.all()] == ["nova@example.com"]


def test_delete_removes_the_document_and_all_of_its_signers(api: APIClient) -> None:
    document = DocumentFactory.create()
    SignerFactory.create_batch(2, document=document)

    response = api.delete(f"{ENDPOINT}{document.pk}/")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Document.objects.filter(pk=document.pk).exists()
    assert Signer.objects.filter(document_id=document.pk).count() == 0


def test_resync_is_rejected_while_an_attempt_is_in_flight(api: APIClient) -> None:
    document = DocumentFactory.create(provider_status=ProviderStatus.PENDING_INTEGRATION)

    response = api.post(f"{ENDPOINT}{document.pk}/resync/")

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data["code"] == "resync_not_allowed"


def test_resync_returns_the_updated_document(api: APIClient) -> None:
    document = DocumentFactory.create(provider_status=ProviderStatus.FAILED)

    response = api.post(f"{ENDPOINT}{document.pk}/resync/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == str(document.pk)
    assert response.data["provider_status"] in {ProviderStatus.SUBMITTED, ProviderStatus.FAILED}


def test_every_document_route_requires_authentication(anonymous_api: APIClient) -> None:
    document = DocumentFactory.create()

    assert anonymous_api.get(ENDPOINT).status_code == status.HTTP_401_UNAUTHORIZED
    assert anonymous_api.post(ENDPOINT, {}, format="json").status_code == 401
    assert anonymous_api.get(f"{ENDPOINT}{document.pk}/").status_code == 401
    assert anonymous_api.post(f"{ENDPOINT}{document.pk}/resync/").status_code == 401
