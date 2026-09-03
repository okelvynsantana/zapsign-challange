"""T082 — report aggregation (US4: FR-025, FR-026, research.md §15)."""

import pytest

from apps.documents.reports import document_report, summary_report
from apps.documents.services import analyze_document
from apps.documents.status import ProviderStatus
from apps.documents.tests.factories import DocumentFactory
from apps.integrations.analysis.clause_checker import ClauseChecker
from apps.integrations.analysis.fakes import FakeAnalysisProvider
from apps.integrations.analysis.pipeline import AnalysisPipeline
from apps.integrations.analysis.provider import ProviderAnalysis
from apps.integrations.analysis.results import Insight
from apps.integrations.pdf.extractor import PdfExtractionError
from apps.integrations.pdf.fakes import FakePdfTextExtractor
from apps.signers.tests.factories import SignerFactory

pytestmark = pytest.mark.django_db


def _pipeline(
    *, risk: bool = True, fail: bool = False, summary: str = "Resumo do contrato."
) -> AnalysisPipeline:
    extractor_outcomes = [PdfExtractionError("no_text", "scanned")] if fail else []
    return AnalysisPipeline(
        extractor=FakePdfTextExtractor(extractor_outcomes),
        provider=FakeAnalysisProvider(
            [
                ProviderAnalysis(
                    summary=summary,
                    missing_topics=["foro"],
                    insights=[Insight(text="Multa desproporcional.", risk=risk)],
                    model="fake-model",
                )
            ]
        ),
        clause_checker=ClauseChecker(),
    )


# -- per-document report ----------------------------------------------------------------


def test_the_document_report_carries_status_and_the_latest_analysis() -> None:
    document = DocumentFactory.create(provider_status=ProviderStatus.SUBMITTED, status="pending")
    SignerFactory.create(document=document, name="Ana", email="ana@example.com")
    analyze_document(document, pipeline=_pipeline())

    report = document_report(document)

    assert report["document_id"] == document.pk
    assert report["provider_status"] == ProviderStatus.SUBMITTED
    assert report["signature_status"] == "pending"
    assert report["latest_analysis"].summary == "Resumo do contrato."
    assert [s.email for s in report["signers"]] == ["ana@example.com"]


def test_the_document_report_reflects_only_the_newest_analysis() -> None:
    document = DocumentFactory.create()
    analyze_document(document, pipeline=_pipeline(summary="Primeira."))
    analyze_document(document, pipeline=_pipeline(summary="Segunda."))

    assert document_report(document)["latest_analysis"].summary == "Segunda."


def test_a_document_with_no_analysis_reports_none() -> None:
    assert document_report(DocumentFactory.create())["latest_analysis"] is None


# -- aggregated report ------------------------------------------------------------------


def test_the_summary_groups_documents_by_provider_status() -> None:
    DocumentFactory.create_batch(2, provider_status=ProviderStatus.SUBMITTED)
    DocumentFactory.create(provider_status=ProviderStatus.FAILED)

    summary = summary_report()

    assert summary["total_documents"] == 3
    assert summary["by_provider_status"]["submitted"] == 2
    assert summary["by_provider_status"]["failed"] == 1
    assert summary["by_provider_status"]["pending_integration"] == 0


def test_the_summary_groups_documents_by_signature_status() -> None:
    DocumentFactory.create(status="signed")
    DocumentFactory.create(status="pending")
    DocumentFactory.create(status="")

    by_signature = summary_report()["by_signature_status"]

    assert by_signature["signed"] == 1
    assert by_signature["pending"] == 1
    assert by_signature["unknown"] == 1


def test_the_summary_counts_documents_whose_latest_analysis_flags_a_risk() -> None:
    risky = DocumentFactory.create()
    analyze_document(risky, pipeline=_pipeline(risk=True))
    calm = DocumentFactory.create()
    analyze_document(calm, pipeline=_pipeline(risk=False))

    assert summary_report()["documents_with_risk_insight"] == 1


def test_a_risk_superseded_by_a_clean_rerun_stops_counting() -> None:
    document = DocumentFactory.create()
    analyze_document(document, pipeline=_pipeline(risk=True))
    analyze_document(document, pipeline=_pipeline(risk=False))

    assert summary_report()["documents_with_risk_insight"] == 0


def test_the_summary_lists_recent_risk_insights_with_their_document() -> None:
    document = DocumentFactory.create(name="Contrato de Risco")
    analyze_document(document, pipeline=_pipeline(risk=True))

    (insight,) = summary_report()["recent_risk_insights"]

    assert insight["document_id"] == document.pk
    assert insight["name"] == "Contrato de Risco"
    assert insight["text"] == "Multa desproporcional."
    assert insight["created_at"] is not None


def test_a_failed_latest_analysis_contributes_no_risk() -> None:
    document = DocumentFactory.create()
    analyze_document(document, pipeline=_pipeline(fail=True))

    summary = summary_report()

    assert summary["documents_with_risk_insight"] == 0
    assert summary["recent_risk_insights"] == []


def test_an_empty_dataset_returns_a_well_formed_summary() -> None:
    summary = summary_report()

    assert summary["total_documents"] == 0
    assert summary["by_provider_status"] == {
        "pending_integration": 0,
        "submitted": 0,
        "failed": 0,
    }
    assert summary["by_signature_status"] == {}
    assert summary["documents_with_risk_insight"] == 0
    assert summary["recent_risk_insights"] == []
    assert summary["generated_at"] is not None
