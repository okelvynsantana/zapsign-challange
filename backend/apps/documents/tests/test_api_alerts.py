"""T093 — `GET /api/alerts/` (bonus US5: FR-030, US5 AS-1 … AS-3)."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.documents.models import Document
from apps.documents.tests.factories import DocumentFactory

pytestmark = pytest.mark.django_db

ENDPOINT = "/api/alerts/"


def _age(document: Document, days: int) -> Document:
    Document.objects.filter(pk=document.pk).update(created_at=timezone.now() - timedelta(days=days))
    return document


def test_a_stalled_document_appears_with_the_documented_shape(api: APIClient, settings) -> None:
    settings.ALERT_STALLED_DAYS = 5
    document = _age(DocumentFactory.create(status="pending", name="Contrato parado"), days=9)

    response = api.get(ENDPOINT)

    assert response.status_code == status.HTTP_200_OK
    (alert,) = response.data
    assert set(alert) == {"type", "document_id", "document_name", "detail", "since"}
    assert alert["type"] == "stalled"
    assert alert["document_id"] == str(document.pk)
    assert alert["document_name"] == "Contrato parado"


def test_nothing_matching_returns_an_empty_list_not_an_error(api: APIClient, settings) -> None:
    settings.ALERT_STALLED_DAYS = 30
    DocumentFactory.create(status="pending")

    response = api.get(ENDPOINT)

    assert response.status_code == status.HTTP_200_OK
    assert response.data == []


def test_the_dashboard_requires_authentication(anonymous_api: APIClient) -> None:
    assert anonymous_api.get(ENDPOINT).status_code == status.HTTP_401_UNAUTHORIZED
