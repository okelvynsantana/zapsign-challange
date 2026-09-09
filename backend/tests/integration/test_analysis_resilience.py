"""T069 — an analysis failure never costs the document (SC-010, FR-019, FR-020).

Drives the whole create flow through the API with a pipeline whose PDF fetch fails, and
asserts the document — and its ZapSign state — come through untouched.
"""

from typing import Any

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.companies.tests.factories import CompanyFactory
from apps.documents.models import Document, DocumentAnalysis
from apps.documents.status import ProviderStatus
from apps.integrations.analysis.clause_checker import ClauseChecker
from apps.integrations.analysis.fakes import FakeAnalysisProvider
from apps.integrations.analysis.pipeline import AnalysisPipeline
from apps.integrations.analysis.provider import AnalysisProviderError
from apps.integrations.pdf.extractor import PdfExtractionError
from apps.integrations.pdf.fakes import FakePdfTextExtractor

pytestmark = pytest.mark.django_db


def _install_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    *,
    extractor_outcomes: list[object] | None = None,
    provider_outcomes: list[object] | None = None,
    regex_fallback_enabled: bool = True,
) -> None:
    """Point the view's pipeline factory at a scripted pipeline."""
    from apps.documents import views

    def factory() -> AnalysisPipeline:
        return AnalysisPipeline(
            extractor=FakePdfTextExtractor(list(extractor_outcomes or [])),  # type: ignore[arg-type]
            provider=FakeAnalysisProvider(list(provider_outcomes or [])),  # type: ignore[arg-type]
            clause_checker=ClauseChecker(),
            regex_fallback_enabled=regex_fallback_enabled,
        )

    monkeypatch.setattr(views, "get_analysis_pipeline", factory)


def _create(api: APIClient) -> dict[str, Any]:
    response = api.post(
        "/api/documents/",
        {
            "company": str(CompanyFactory.create().pk),
            "name": "Contrato X",
            "pdf_url": "https://files.example.test/contrato.pdf",
            "signers": [{"name": "Ana Souza", "email": "ana@example.com"}],
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.data


def test_an_unreachable_pdf_still_yields_a_created_document(
    api: APIClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_pipeline(
        monkeypatch,
        extractor_outcomes=[PdfExtractionError("unreachable", "404 from the PDF host")],
    )

    body = _create(api)

    assert body["latest_analysis"]["state"] == "failed"
    assert body["latest_analysis"]["error_reason"] == "unreachable"
    assert Document.objects.filter(pk=body["id"]).exists()


def test_the_zapsign_state_is_untouched_by_an_analysis_failure(
    api: APIClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_pipeline(monkeypatch, extractor_outcomes=[PdfExtractionError("no_text", "scanned")])

    body = _create(api)
    document = Document.objects.get(pk=body["id"])

    assert document.provider_status == ProviderStatus.SUBMITTED
    assert document.last_provider_error == ""


def test_a_failed_analysis_is_retryable_and_appends(
    api: APIClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_pipeline(monkeypatch, extractor_outcomes=[PdfExtractionError("timeout", "slow host")])
    body = _create(api)

    _install_pipeline(monkeypatch)  # the PDF host is back
    retried = api.post(f"/api/documents/{body['id']}/analyze/")

    assert retried.status_code == status.HTTP_201_CREATED
    assert retried.data["state"] == "succeeded"
    assert DocumentAnalysis.objects.filter(document_id=body["id"]).count() == 2


def test_a_provider_outage_degrades_to_the_regex_pass(
    api: APIClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_pipeline(
        monkeypatch, provider_outcomes=[AnalysisProviderError("timeout", "model too slow")]
    )

    body = _create(api)

    assert body["latest_analysis"]["state"] == "succeeded"
    assert body["latest_analysis"]["source"] == "regex"
    assert body["latest_analysis"]["missing_topics"]


def test_a_provider_outage_with_the_fallback_off_records_a_failed_analysis(
    api: APIClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_pipeline(
        monkeypatch,
        provider_outcomes=[AnalysisProviderError("auth", "bad key")],
        regex_fallback_enabled=False,
    )

    body = _create(api)

    assert body["latest_analysis"]["state"] == "failed"
    assert body["latest_analysis"]["error_reason"] == "provider_auth"
    assert body["provider_status"] == ProviderStatus.SUBMITTED
