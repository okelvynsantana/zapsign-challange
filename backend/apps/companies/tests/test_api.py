"""T030 — `/api/companies/` CRUD and credential masking (US1: FR-001, FR-002, FR-012)."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.companies.models import Company
from apps.companies.tests.factories import CompanyFactory

pytestmark = pytest.mark.django_db

ENDPOINT = "/api/companies/"


def test_create_returns_the_resource_without_the_credential(api: APIClient) -> None:
    response = api.post(
        ENDPOINT,
        {"name": "Acme Ltda", "api_token": "zapsign-sandbox-token-3f9a"},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["name"] == "Acme Ltda"
    assert "api_token" not in response.data
    assert response.data["api_token_masked"].endswith("3f9a")
    assert Company.objects.get(pk=response.data["id"]).api_token == "zapsign-sandbox-token-3f9a"


def test_create_requires_a_name_and_a_credential(api: APIClient) -> None:
    response = api.post(ENDPOINT, {"name": ""}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "validation_error"
    assert set(response.data["fields"]) == {"name", "api_token"}


def test_list_never_exposes_the_credential(api: APIClient) -> None:
    CompanyFactory.create(api_token="zapsign-sandbox-token-beef")

    response = api.get(ENDPOINT)

    assert response.status_code == status.HTTP_200_OK
    (item,) = response.data["results"]
    assert "api_token" not in item
    assert item["api_token_masked"].endswith("beef")


def test_patching_the_name_alone_preserves_the_stored_credential(api: APIClient) -> None:
    company = CompanyFactory.create(name="Acme Ltda", api_token="keep-this-token")

    response = api.patch(f"{ENDPOINT}{company.pk}/", {"name": "Acme S.A."}, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["name"] == "Acme S.A."
    company.refresh_from_db()
    assert company.api_token == "keep-this-token"


def test_a_blank_credential_on_update_preserves_the_stored_one(api: APIClient) -> None:
    company = CompanyFactory.create(api_token="keep-this-token")

    response = api.patch(f"{ENDPOINT}{company.pk}/", {"api_token": ""}, format="json")

    assert response.status_code == status.HTTP_200_OK
    company.refresh_from_db()
    assert company.api_token == "keep-this-token"


def test_the_credential_can_be_rotated(api: APIClient) -> None:
    company = CompanyFactory.create(api_token="old-token")

    api.patch(f"{ENDPOINT}{company.pk}/", {"api_token": "new-token-9999"}, format="json")

    company.refresh_from_db()
    assert company.api_token == "new-token-9999"


def test_delete_removes_a_company_with_no_documents(api: APIClient) -> None:
    company = CompanyFactory.create()

    response = api.delete(f"{ENDPOINT}{company.pk}/")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Company.objects.filter(pk=company.pk).exists()


def test_every_company_route_requires_authentication(anonymous_api: APIClient) -> None:
    company = CompanyFactory.create()

    assert anonymous_api.get(ENDPOINT).status_code == status.HTTP_401_UNAUTHORIZED
    unauthorized = status.HTTP_401_UNAUTHORIZED
    assert anonymous_api.post(ENDPOINT, {}, format="json").status_code == unauthorized
    detail = f"{ENDPOINT}{company.pk}/"
    assert anonymous_api.get(detail).status_code == status.HTTP_401_UNAUTHORIZED
    assert anonymous_api.delete(detail).status_code == status.HTTP_401_UNAUTHORIZED
