"""T019 — `/api/health/` behaviour (FR-027, research.md §11)."""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def client() -> APIClient:
    return APIClient()


def test_returns_200_with_database_ok(client: APIClient) -> None:
    response = client.get(reverse("core:health"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == "ok"
    assert response.data["checks"]["database"] == "ok"


def test_requires_no_authentication(client: APIClient) -> None:
    # No credentials set on the client at all — infra probes carry none.
    assert client.get(reverse("core:health")).status_code == status.HTTP_200_OK


def test_returns_503_when_the_database_check_fails(
    client: APIClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode() -> None:
        raise RuntimeError("connection refused")

    monkeypatch.setattr("apps.core.health.connection.cursor", explode)

    response = client.get(reverse("core:health"))

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.data["status"] == "unavailable"
    assert response.data["checks"]["database"] == "error"


def test_provider_checks_are_skipped_by_default(client: APIClient) -> None:
    # The suite and CI must never reach a third party (Constitution Principle II).
    checks = client.get(reverse("core:health")).data["checks"]

    assert checks["zapsign"] == "skipped"
    assert checks["openai"] == "skipped"


def test_provider_failure_does_not_fail_the_endpoint(
    client: APIClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "apps.core.health._check_providers",
        lambda: {"zapsign": "error", "openai": "error"},
    )

    response = client.get(reverse("core:health"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == "ok"
    assert response.data["checks"]["zapsign"] == "error"
