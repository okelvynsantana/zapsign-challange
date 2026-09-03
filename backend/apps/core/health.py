"""Unauthenticated health endpoint for Kubernetes probes (FR-027, research.md §11).

Database reachability is the readiness signal for this service: only a failing DB check
returns ``503``. Provider checks are best-effort and time-boxed — a ZapSign or OpenAI
outage must never cycle our pods. They are skipped unless ``HEALTH_CHECK_INTEGRATIONS`` is
enabled, so neither the test suite nor CI ever reaches a third party.
"""

import logging
from typing import Any

import httpx
from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.schema import HealthSerializer
from apps.integrations.config import get_integrations_config
from config.settings.env import env_bool

__all__ = ["HealthView"]

logger = logging.getLogger("api.health")

PROVIDER_PROBE_TIMEOUT_SECONDS = 2.0
OPENAI_PROBE_URL = "https://api.openai.com/v1/models"

STATUS_OK = "ok"
STATUS_ERROR = "error"
STATUS_SKIPPED = "skipped"


def _check_database() -> str:
    """Return ``ok`` when a trivial query succeeds against the default connection."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        logger.exception("health_database_check_failed")
        return STATUS_ERROR
    return STATUS_OK


def _probe(url: str) -> str:
    """Best-effort reachability probe; any failure is reported, never raised."""
    try:
        response = httpx.head(
            url,
            timeout=PROVIDER_PROBE_TIMEOUT_SECONDS,
            follow_redirects=True,
        )
    except Exception:
        return STATUS_ERROR
    reachable = response.status_code < status.HTTP_500_INTERNAL_SERVER_ERROR
    return STATUS_OK if reachable else STATUS_ERROR


def _check_providers() -> dict[str, str]:
    """Return the per-provider check results, or ``skipped`` when probing is disabled."""
    if not env_bool("HEALTH_CHECK_INTEGRATIONS", False):
        return {"zapsign": STATUS_SKIPPED, "openai": STATUS_SKIPPED}

    config = get_integrations_config()
    return {
        "zapsign": STATUS_SKIPPED if config.zapsign.use_fake else _probe(config.zapsign.base_url),
        "openai": _probe(OPENAI_PROBE_URL) if config.analysis.api_key else STATUS_SKIPPED,
    }


class HealthView(APIView):
    """``GET /api/health/`` — no credentials, for liveness/readiness probes."""

    authentication_classes: list[Any] = []
    permission_classes = [AllowAny]

    @extend_schema(responses={200: HealthSerializer, 503: HealthSerializer})
    def get(self, request: Request) -> Response:
        checks = {"database": _check_database(), **_check_providers()}
        database_ok = checks["database"] == STATUS_OK
        return Response(
            {
                "status": STATUS_OK if database_ok else "unavailable",
                "checks": checks,
            },
            status=status.HTTP_200_OK if database_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
        )
