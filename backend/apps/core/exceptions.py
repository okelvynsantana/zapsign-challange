"""Uniform API error bodies.

Every error response in this API is ``{"detail": str, "code": str, "fields": {...}?}`` as
fixed by ``contracts/rest-api.md``. ``fields`` is present only for ``400`` validation
errors. DRF's default handler produces several different shapes, so this module
normalises them in one place.
"""

from typing import Any

from django.db.models import ProtectedError
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

__all__ = ["ConflictError", "api_exception_handler"]


class ConflictError(APIException):
    """A request that is valid but conflicts with the resource's current state."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "The request conflicts with the current state of the resource."
    default_code = "conflict"

    def __init__(self, detail: str | None = None, code: str | None = None) -> None:
        super().__init__(detail=detail, code=code)
        self.code = code or self.default_code


def _flatten_field_errors(detail: Any) -> dict[str, list[str]]:
    """Reduce DRF's nested validation detail into ``{field: [messages]}``."""
    if not isinstance(detail, dict):
        return {}
    fields: dict[str, list[str]] = {}
    for key, value in detail.items():
        if isinstance(value, list):
            fields[str(key)] = [str(item) for item in value]
        elif isinstance(value, dict):
            for nested_key, nested_value in _flatten_field_errors(value).items():
                fields[f"{key}.{nested_key}"] = nested_value
        else:
            fields[str(key)] = [str(value)]
    return fields


def _detail_message(detail: Any, fallback: str) -> str:
    """Return a single human-readable sentence for ``detail``."""
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list) and detail:
        return str(detail[0])
    if isinstance(detail, dict):
        for value in detail.values():
            return _detail_message(value, fallback)
    return fallback


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """DRF ``EXCEPTION_HANDLER`` producing the contract's standard error body."""
    if isinstance(exc, ProtectedError):
        exc = ConflictError(
            detail="This resource is referenced by other records and cannot be deleted.",
            code="protected_reference",
        )

    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    detail = getattr(exc, "detail", response.data)

    if isinstance(exc, ValidationError):
        body: dict[str, Any] = {
            "detail": "The request payload failed validation.",
            "code": "validation_error",
            "fields": _flatten_field_errors(detail),
        }
        if not body["fields"]:
            body["detail"] = _detail_message(detail, body["detail"])
            body.pop("fields")
        response.data = body
        return response

    code = getattr(exc, "code", None) or getattr(getattr(exc, "detail", None), "code", None)
    default_code = getattr(exc, "default_code", "error")
    response.data = {
        "detail": _detail_message(detail, "An error occurred."),
        "code": str(code or default_code),
    }
    return response
