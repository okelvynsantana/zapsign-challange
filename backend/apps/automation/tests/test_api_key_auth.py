"""T026 — API-key authentication and permission behaviour (FR-023, FR-024, US4 AS-5/AS-6)."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView
from rest_framework_api_key.models import APIKey

from apps.automation.auth import ApiKeyAuthentication, HasApiKey, api_key_name

pytestmark = pytest.mark.django_db


class _ProtectedView(APIView):
    """Stands in for any `/api/automation/**` endpoint."""

    authentication_classes = [ApiKeyAuthentication]
    permission_classes = [HasApiKey]

    def get(self, request: Request) -> Response:
        return Response({"key_name": api_key_name(request)})


view = _ProtectedView.as_view()
factory = APIRequestFactory()


def _call(authorization: str | None = None) -> Response:
    if authorization is None:
        return view(factory.get("/api/automation/probe/"))
    return view(factory.get("/api/automation/probe/", HTTP_AUTHORIZATION=authorization))


def test_valid_key_is_accepted() -> None:
    _, key = APIKey.objects.create_key(name="n8n")

    response = _call(f"Api-Key {key}")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["key_name"] == "n8n"


def test_missing_credential_is_rejected() -> None:
    response = _call()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "key_name" not in response.data


def test_malformed_credential_is_rejected() -> None:
    assert _call("Api-Key ").status_code == status.HTTP_401_UNAUTHORIZED
    assert _call("Api-Key not-a-real-key").status_code == status.HTTP_401_UNAUTHORIZED
    assert _call("garbage").status_code == status.HTTP_401_UNAUTHORIZED


def test_jwt_is_not_accepted_on_an_api_key_endpoint() -> None:
    # An integration key and a SPA session are separate schemes (contracts/rest-api.md).
    response = _call("Bearer some.jwt.value")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "key_name" not in response.data


def test_revoked_key_is_forbidden() -> None:
    api_key, key = APIKey.objects.create_key(name="retired-integration")
    api_key.revoked = True
    api_key.save()

    response = _call(f"Api-Key {key}")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "key_name" not in response.data


def test_expired_key_is_rejected() -> None:
    _, key = APIKey.objects.create_key(
        name="expired",
        expiry_date=timezone.now() - timedelta(days=1),
    )

    response = _call(f"Api-Key {key}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "key_name" not in response.data


def test_rejection_body_carries_the_standard_error_shape() -> None:
    response = _call()

    assert set(response.data) == {"detail", "code"}
