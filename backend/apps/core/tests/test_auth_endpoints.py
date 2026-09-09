"""The SPA token endpoints, including the contract's error body."""

import pytest
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

TOKEN_URL = "/api/auth/token/"


def test_valid_credentials_return_an_access_and_refresh_pair(
    manager: User, anonymous_api: APIClient
) -> None:
    response = anonymous_api.post(
        TOKEN_URL,
        {"username": "manager", "password": "manager-password"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert {"access", "refresh"} <= set(response.data)


def test_a_rejected_sign_in_uses_the_documented_code(
    manager: User, anonymous_api: APIClient
) -> None:
    response = anonymous_api.post(
        TOKEN_URL, {"username": "manager", "password": "wrong"}, format="json"
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.data["code"] == "invalid_credentials"
    assert "access" not in response.data


def test_an_unknown_user_is_rejected_the_same_way(anonymous_api: APIClient) -> None:
    response = anonymous_api.post(TOKEN_URL, {"username": "nobody", "password": "x"}, format="json")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.data["code"] == "invalid_credentials"


def test_a_refresh_token_yields_a_new_access_token(manager: User, anonymous_api: APIClient) -> None:
    refresh = anonymous_api.post(
        TOKEN_URL,
        {"username": "manager", "password": "manager-password"},
        format="json",
    ).data["refresh"]

    response = anonymous_api.post("/api/auth/token/refresh/", {"refresh": refresh}, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data
