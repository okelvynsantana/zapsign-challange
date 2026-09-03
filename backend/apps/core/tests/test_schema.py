"""T107 — the published OpenAPI schema stays in step with the contract."""

import pytest
import yaml
from django.conf import settings
from rest_framework import status
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

CONTRACT_FILE = (
    settings.BASE_DIR.parent
    / "specs"
    / "001-document-signature-management"
    / "contracts"
    / "openapi.yaml"
)


@pytest.fixture
def schema() -> dict:
    from drf_spectacular.generators import SchemaGenerator

    return SchemaGenerator().get_schema(request=None, public=True)


def test_the_schema_generates_without_errors(schema: dict) -> None:
    assert schema["info"]["title"]
    assert schema["paths"]


def test_every_contract_path_is_implemented(schema: dict) -> None:
    contract = yaml.safe_load(CONTRACT_FILE.read_text())
    implemented = set(schema["paths"])

    missing = [path for path in contract["paths"] if f"/api{path}" not in implemented]

    assert missing == []


def test_both_credential_schemes_are_described(schema: dict) -> None:
    schemes = schema["components"]["securitySchemes"]

    assert "ApiKeyAuth" in schemes
    assert schemes["ApiKeyAuth"]["in"] == "header"
    assert "jwtAuth" in schemes


def test_the_schema_endpoint_is_served(api: APIClient) -> None:
    response = api.get("/api/schema/")

    assert response.status_code == status.HTTP_200_OK
