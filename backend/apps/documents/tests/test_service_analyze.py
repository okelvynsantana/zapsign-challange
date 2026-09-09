"""T067 — `analyze_document` persistence rules (US3: FR-017, FR-019, FR-020)."""

import pytest

from apps.documents.models import DocumentAnalysis
from apps.documents.services import analyze_document
from apps.documents.status import ProviderStatus
from apps.documents.tests.factories import DocumentFactory
from apps.integrations.analysis.clause_checker import ClauseChecker
from apps.integrations.analysis.fakes import FakeAnalysisProvider
from apps.integrations.analysis.pipeline import AnalysisPipeline
from apps.integrations.analysis.provider import AnalysisProviderError
from apps.integrations.pdf.extractor import PdfExtractionError
from apps.integrations.pdf.fakes import FakePdfTextExtractor

pytestmark = pytest.mark.django_db


def _pipeline(
    extractor_outcomes: list[object] | None = None,
    provider_outcomes: list[object] | None = None,
    *,
    regex_fallback_enabled: bool = True,
) -> AnalysisPipeline:
    return AnalysisPipeline(
        extractor=FakePdfTextExtractor(extractor_outcomes or []),  # type: ignore[arg-type]
        provider=FakeAnalysisProvider(provider_outcomes or []),  # type: ignore[arg-type]
        clause_checker=ClauseChecker(),
        regex_fallback_enabled=regex_fallback_enabled,
    )


def test_a_run_inserts_exactly_one_analysis() -> None:
    document = DocumentFactory.create()

    analysis = analyze_document(document, pipeline=_pipeline())

    assert DocumentAnalysis.objects.count() == 1
    assert analysis.document_id == document.pk
    assert analysis.state == DocumentAnalysis.State.SUCCEEDED
    assert analysis.summary


def test_a_second_run_appends_and_leaves_the_first_untouched() -> None:
    document = DocumentFactory.create()
    first = analyze_document(document, pipeline=_pipeline())
    first_snapshot = (first.summary, first.created_at, first.state)

    second = analyze_document(document, pipeline=_pipeline())

    assert DocumentAnalysis.objects.filter(document=document).count() == 2
    first.refresh_from_db()
    assert (first.summary, first.created_at, first.state) == first_snapshot
    assert second.pk != first.pk


def test_the_latest_analysis_is_the_newest_row() -> None:
    document = DocumentFactory.create()
    analyze_document(document, pipeline=_pipeline())
    newest = analyze_document(document, pipeline=_pipeline())

    assert document.latest_analysis is not None
    assert document.latest_analysis.pk == newest.pk


def test_a_failed_pipeline_still_records_an_analysis() -> None:
    document = DocumentFactory.create()

    analysis = analyze_document(
        document,
        pipeline=_pipeline(extractor_outcomes=[PdfExtractionError("no_text", "scanned")]),
    )

    assert analysis.state == DocumentAnalysis.State.FAILED
    assert analysis.error_reason == "no_text"
    assert analysis.summary == ""


def test_an_analysis_failure_never_touches_the_document_provider_state() -> None:
    document = DocumentFactory.create(provider_status=ProviderStatus.SUBMITTED, token="doc-token")

    analyze_document(
        document,
        pipeline=_pipeline(extractor_outcomes=[PdfExtractionError("unreachable", "404")]),
    )
    document.refresh_from_db()

    assert document.provider_status == ProviderStatus.SUBMITTED
    assert document.token == "doc-token"
    assert document.last_provider_error == ""


def test_a_provider_outage_is_recorded_with_its_source() -> None:
    document = DocumentFactory.create()

    analysis = analyze_document(
        document,
        pipeline=_pipeline(
            provider_outcomes=[AnalysisProviderError("timeout", "too slow")],
        ),
    )

    assert analysis.state == DocumentAnalysis.State.SUCCEEDED
    assert analysis.source == DocumentAnalysis.Source.REGEX
    assert analysis.model == ""


def test_the_risk_flag_is_derived_from_the_latest_analysis() -> None:
    document = DocumentFactory.create()

    analyze_document(document, pipeline=_pipeline())

    assert document.has_open_risk is True


def test_a_failed_latest_analysis_does_not_count_as_a_risk() -> None:
    document = DocumentFactory.create()
    analyze_document(document, pipeline=_pipeline())
    analyze_document(
        document,
        pipeline=_pipeline(extractor_outcomes=[PdfExtractionError("no_text", "scanned")]),
    )

    assert document.has_open_risk is False
