"""T068 — the analysis endpoints (US3: FR-015, FR-016, FR-017, FR-018)."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.documents.models import DocumentAnalysis
from apps.documents.tests.factories import DocumentFactory

pytestmark = pytest.mark.django_db


def test_analyze_creates_a_new_analysis(api: APIClient) -> None:
    document = DocumentFactory.create()

    response = api.post(f"/api/documents/{document.pk}/analyze/")

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["state"] in {"succeeded", "failed"}
    assert DocumentAnalysis.objects.filter(document=document).count() == 1


def test_analyzing_twice_grows_the_history_by_exactly_one(api: APIClient) -> None:
    document = DocumentFactory.create()
    api.post(f"/api/documents/{document.pk}/analyze/")
    first_id = DocumentAnalysis.objects.get().pk

    api.post(f"/api/documents/{document.pk}/analyze/")

    assert DocumentAnalysis.objects.filter(document=document).count() == 2
    assert DocumentAnalysis.objects.filter(pk=first_id).exists()


def test_the_history_endpoint_returns_newest_first(api: APIClient) -> None:
    document = DocumentFactory.create()
    api.post(f"/api/documents/{document.pk}/analyze/")
    api.post(f"/api/documents/{document.pk}/analyze/")

    response = api.get(f"/api/documents/{document.pk}/analyses/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2
    timestamps = [item["created_at"] for item in response.data["results"]]
    assert timestamps == sorted(timestamps, reverse=True)


def test_the_document_detail_embeds_the_latest_analysis(api: APIClient) -> None:
    document = DocumentFactory.create()
    api.post(f"/api/documents/{document.pk}/analyze/")
    newest = api.post(f"/api/documents/{document.pk}/analyze/").data

    response = api.get(f"/api/documents/{document.pk}/")

    assert response.data["latest_analysis"]["id"] == newest["id"]


def test_a_document_with_no_analysis_reports_null(api: APIClient) -> None:
    document = DocumentFactory.create()

    response = api.get(f"/api/documents/{document.pk}/")

    assert response.data["latest_analysis"] is None


def test_the_analysis_resource_carries_the_full_contract_shape(api: APIClient) -> None:
    document = DocumentFactory.create()

    body = api.post(f"/api/documents/{document.pk}/analyze/").data

    assert set(body) == {
        "id",
        "state",
        "summary",
        "missing_topics",
        "insights",
        "source",
        "model",
        "error_reason",
        "created_at",
    }
    assert isinstance(body["missing_topics"], list)
    assert all({"text", "risk"} <= set(item) for item in body["insights"])


def test_analyze_on_a_missing_document_is_404(api: APIClient) -> None:
    missing = "00000000-0000-4000-8000-000000000000"

    assert api.post(f"/api/documents/{missing}/analyze/").status_code == status.HTTP_404_NOT_FOUND


def test_the_analysis_endpoints_require_authentication(anonymous_api: APIClient) -> None:
    document = DocumentFactory.create()

    assert anonymous_api.post(f"/api/documents/{document.pk}/analyze/").status_code == 401
    assert anonymous_api.get(f"/api/documents/{document.pk}/analyses/").status_code == 401


def test_analyses_are_deleted_with_their_document(api: APIClient) -> None:
    document = DocumentFactory.create()
    api.post(f"/api/documents/{document.pk}/analyze/")

    api.delete(f"/api/documents/{document.pk}/")

    assert DocumentAnalysis.objects.count() == 0
