"""OpenAPI description of the API-key scheme, for `drf-spectacular`.

Without this extension the generator cannot describe `ApiKeyAuthentication`, and the
published schema would silently omit the credential every automation call needs.
"""

from typing import Any

from drf_spectacular.extensions import OpenApiAuthenticationExtension

__all__ = ["ApiKeyAuthenticationScheme"]


class ApiKeyAuthenticationScheme(OpenApiAuthenticationExtension):
    """Documents `Authorization: Api-Key <key>` as an API-key security scheme."""

    target_class = "apps.automation.auth.ApiKeyAuthentication"
    name = "ApiKeyAuth"

    def get_security_definition(self, auto_schema: Any) -> dict[str, Any]:
        return {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "Revocable per-integration key, sent as `Api-Key <key>`.",
        }
