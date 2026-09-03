"""Pytest bootstrap: make `backend/` importable so `config` and `apps` resolve.

Shared fixtures that every app needs (an authenticated API client, the internal user)
live here; anything app-specific belongs to that app's `tests/` package.
"""

import os
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

BACKEND_ROOT: Path = Path(__file__).resolve().parent

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture(autouse=True)
def _offline_providers(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Force every integration to its fake for the whole suite.

    Constitution Principle II: the tests — and CI — must never reach a third party. Tests
    that want a specific provider behaviour install their own gateway or patch
    `apps.integrations.providers`.
    """
    from apps.integrations.config import get_integrations_config

    monkeypatch.setitem(os.environ, "ZAPSIGN_USE_FAKE", "true")
    monkeypatch.setitem(os.environ, "AI_USE_FAKE", "true")
    monkeypatch.setitem(os.environ, "N8N_WEBHOOK_URL", "")
    get_integrations_config.cache_clear()
    yield
    get_integrations_config.cache_clear()


@pytest.fixture
def manager(db) -> User:
    """The internal manager the SPA authenticates as."""
    return User.objects.create_user(username="manager", password="manager-password")


@pytest.fixture
def api(manager: User) -> APIClient:
    """An `APIClient` carrying a valid JWT for `manager`."""
    from rest_framework_simplejwt.tokens import RefreshToken

    client = APIClient()
    access = RefreshToken.for_user(manager).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


@pytest.fixture
def anonymous_api() -> APIClient:
    """An `APIClient` with no credentials at all."""
    return APIClient()
