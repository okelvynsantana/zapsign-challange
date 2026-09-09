"""API-key authentication for external automation callers (FR-023, FR-024).

`Authorization: Api-Key <key>`. Keys are hashed at rest by `djangorestframework-api-key`,
carry a name, and are individually revocable. This scheme is deliberately separate from
the SPA's JWT: an integration key can never act as a full session, and a JWT is never
accepted on `/api/automation/**`.

Status mapping fixed by `contracts/rest-api.md`:

* missing / malformed / unknown / expired key -> ``401`` (unauthenticated)
* revoked key                                 -> ``403`` (the caller was cut off)

In every rejection the body carries no resource data.
"""

from typing import Any

from django.contrib.auth.models import AnonymousUser
from rest_framework import permissions
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework_api_key.models import APIKey

__all__ = ["ApiKeyAuthentication", "HasApiKey", "IsAuthenticatedOrHasApiKey", "api_key_name"]

AUTH_SCHEME = "Api-Key"


def api_key_name(request: Request) -> str:
    """Return the name of the API key that authenticated ``request``, or ``""``."""
    api_key = getattr(request, "auth", None)
    return api_key.name if isinstance(api_key, APIKey) else ""


class ApiKeyAuthentication(BaseAuthentication):
    """Resolve ``Authorization: Api-Key <key>`` to its :class:`APIKey` row."""

    def authenticate(self, request: Request) -> tuple[AnonymousUser, APIKey] | None:
        header = request.headers.get("Authorization", "")
        scheme, _, key = header.partition(" ")

        if scheme != AUTH_SCHEME:
            # Not our scheme (absent, or a JWT): leave the request unauthenticated so the
            # permission class rejects it with 401.
            return None

        key = key.strip()
        if not key:
            raise AuthenticationFailed("Malformed API key.")

        prefix, _, _ = key.partition(".")
        try:
            candidate = APIKey.objects.get(prefix=prefix)
        except APIKey.DoesNotExist as exc:
            raise AuthenticationFailed("Invalid API key.") from exc

        if not candidate.is_valid(key):
            raise AuthenticationFailed("Invalid API key.")
        if candidate.revoked:
            raise PermissionDenied("This API key has been revoked.")
        if candidate.has_expired:
            raise AuthenticationFailed("This API key has expired.")

        return AnonymousUser(), candidate

    def authenticate_header(self, request: Request) -> str:
        # Presence of this header is what makes DRF answer 401 (not 403) for an
        # unauthenticated request.
        return AUTH_SCHEME


class HasApiKey(permissions.BasePermission):
    """Allow only requests carrying a valid, non-revoked API key."""

    message = "A valid API key is required."

    def has_permission(self, request: Request, view: APIView) -> bool:
        api_key: Any = getattr(request, "auth", None)
        return isinstance(api_key, APIKey) and not api_key.revoked


class IsAuthenticatedOrHasApiKey(permissions.BasePermission):
    """Allow an authenticated internal user (JWT) **or** a valid API key.

    Used by the shared read surfaces (`/api/documents/{id}/report/`,
    `/api/reports/summary/`) that both the SPA and automation consume.
    """

    message = "Authentication credentials were not provided."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            return True
        return HasApiKey().has_permission(request, view)
