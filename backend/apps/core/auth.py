"""SPA token endpoint, with the error body the API contract specifies.

`simplejwt` rejects a bad sign-in with the code `no_active_account`. The contract
(`contracts/rest-api.md`) documents `invalid_credentials`, which is also the more accurate
description — the account may well exist. This maps it without touching the token logic.
"""

from typing import Any

from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

__all__ = ["ContractTokenObtainPairSerializer", "ContractTokenObtainPairView"]

INVALID_CREDENTIALS_CODE = "invalid_credentials"


class ContractTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Re-raises a failed sign-in with the documented code."""

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        try:
            return super().validate(attrs)
        except AuthenticationFailed as exc:
            # `exc.detail` is an `ErrorDetail` that already carries simplejwt's code, and
            # DRF preserves that code when re-wrapping it. Pass a plain string so the
            # documented code is the one that sticks.
            raise AuthenticationFailed(
                detail=str(exc.detail),
                code=INVALID_CREDENTIALS_CODE,
            ) from exc


class ContractTokenObtainPairView(TokenObtainPairView):
    """`POST /api/auth/token/`."""

    serializer_class = ContractTokenObtainPairSerializer
