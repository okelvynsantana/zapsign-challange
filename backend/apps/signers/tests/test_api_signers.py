"""T044 — `/api/signers/` standalone surface (US2: FR-006, duplicate-email edge case)."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.documents.tests.factories import DocumentFactory
from apps.signers.models import Signer
from apps.signers.tests.factories import SignerFactory

pytestmark = pytest.mark.django_db

ENDPOINT = "/api/signers/"


def test_create_attaches_a_signer_to_its_document(api: APIClient) -> None:
    document = DocumentFactory.create()

    response = api.post(
        ENDPOINT,
        {"document": str(document.pk), "name": "Ana Souza", "email": "ana@example.com"},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert Signer.objects.get(pk=response.data["id"]).document_id == document.pk


def test_the_same_email_twice_on_one_document_is_rejected(api: APIClient) -> None:
    signer = SignerFactory.create(email="ana@example.com")

    response = api.post(
        ENDPOINT,
        {"document": str(signer.document_id), "name": "Ana again", "email": "ana@example.com"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "email" in str(response.data["fields"])


def test_the_same_email_on_different_documents_is_allowed(api: APIClient) -> None:
    SignerFactory.create(email="ana@example.com")
    other_document = DocumentFactory.create()

    response = api.post(
        ENDPOINT,
        {"document": str(other_document.pk), "name": "Ana", "email": "ana@example.com"},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED


def test_an_invalid_email_is_rejected(api: APIClient) -> None:
    document = DocumentFactory.create()

    response = api.post(
        ENDPOINT,
        {"document": str(document.pk), "name": "Ana", "email": "not-an-email"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "email" in response.data["fields"]


def test_the_list_can_be_filtered_by_document(api: APIClient) -> None:
    wanted = SignerFactory.create()
    SignerFactory.create()

    response = api.get(ENDPOINT, {"document": str(wanted.document_id)})

    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(wanted.pk)


def test_a_signer_can_be_edited_and_deleted(api: APIClient) -> None:
    signer = SignerFactory.create(name="Ana")

    patched = api.patch(f"{ENDPOINT}{signer.pk}/", {"name": "Ana Souza"}, format="json")
    assert patched.status_code == status.HTTP_200_OK
    signer.refresh_from_db()
    assert signer.name == "Ana Souza"

    deleted = api.delete(f"{ENDPOINT}{signer.pk}/")
    assert deleted.status_code == status.HTTP_204_NO_CONTENT
    assert not Signer.objects.filter(pk=signer.pk).exists()


def test_provider_owned_fields_are_read_only(api: APIClient) -> None:
    document = DocumentFactory.create()

    response = api.post(
        ENDPOINT,
        {
            "document": str(document.pk),
            "name": "Ana",
            "email": "ana@example.com",
            "token": "forged-token",
            "status": "signed",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    signer = Signer.objects.get(pk=response.data["id"])
    assert signer.token == ""
    assert signer.status == ""


def test_signer_routes_require_authentication(anonymous_api: APIClient) -> None:
    assert anonymous_api.get(ENDPOINT).status_code == status.HTTP_401_UNAUTHORIZED
