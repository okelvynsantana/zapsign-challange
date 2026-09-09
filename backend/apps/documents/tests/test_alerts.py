"""T092 — alert rules (bonus US5: FR-030, SC-011)."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.documents.alerts import build_alerts
from apps.documents.models import Document
from apps.documents.services import analyze_document
from apps.documents.tests.factories import DocumentFactory
from apps.integrations.analysis.clause_checker import ClauseChecker
from apps.integrations.analysis.fakes import FakeAnalysisProvider
from apps.integrations.analysis.pipeline import AnalysisPipeline
from apps.integrations.analysis.provider import ProviderAnalysis
from apps.integrations.analysis.results import Insight
from apps.integrations.pdf.fakes import FakePdfTextExtractor

pytestmark = pytest.mark.django_db


def _age(document: Document, days: int) -> Document:
    """Back-date `created_at`, which `auto_now_add` otherwise pins to now."""
    Document.objects.filter(pk=document.pk).update(created_at=timezone.now() - timedelta(days=days))
    document.refresh_from_db()
    return document


def _analyze(document: Document, *, risk: bool, text: str = "Multa desproporcional.") -> None:
    analyze_document(
        document,
        pipeline=AnalysisPipeline(
            extractor=FakePdfTextExtractor(),
            provider=FakeAnalysisProvider(
                [
                    ProviderAnalysis(
                        summary="Resumo.",
                        missing_topics=[],
                        insights=[Insight(text=text, risk=risk)],
                        model="fake-model",
                    )
                ]
            ),
            clause_checker=ClauseChecker(),
        ),
    )


# -- stalled ------------------------------------------------------------------------------


def test_a_document_pending_past_the_threshold_is_stalled() -> None:
    document = _age(DocumentFactory.create(status="pending"), days=9)

    (alert,) = build_alerts(stalled_days=5)

    assert alert.type == "stalled"
    assert alert.document_id == document.pk
    assert "9 days" in alert.detail


def test_a_document_inside_the_threshold_is_not_stalled() -> None:
    _age(DocumentFactory.create(status="pending"), days=2)

    assert build_alerts(stalled_days=5) == []


@pytest.mark.parametrize("terminal", ["signed", "refused", "cancelled"])
def test_a_finished_document_is_never_stalled(terminal: str) -> None:
    _age(DocumentFactory.create(status=terminal), days=30)

    assert build_alerts(stalled_days=5) == []


def test_a_document_with_no_signature_status_yet_can_still_stall() -> None:
    _age(DocumentFactory.create(status=""), days=30)

    assert [alert.type for alert in build_alerts(stalled_days=5)] == ["stalled"]


# -- risk ---------------------------------------------------------------------------------


def test_a_risk_insight_in_the_latest_analysis_raises_a_risk_alert() -> None:
    document = DocumentFactory.create(status="pending")
    _analyze(document, risk=True)

    (alert,) = build_alerts(stalled_days=365)

    assert alert.type == "risk"
    assert alert.document_id == document.pk
    assert alert.detail == "Multa desproporcional."


def test_an_insight_with_no_risk_flag_raises_nothing() -> None:
    _analyze(DocumentFactory.create(status="pending"), risk=False)

    assert build_alerts(stalled_days=365) == []


def test_a_clean_rerun_clears_an_earlier_risk() -> None:
    document = DocumentFactory.create(status="pending")
    _analyze(document, risk=True)
    _analyze(document, risk=False)

    assert build_alerts(stalled_days=365) == []


def test_a_document_can_raise_both_kinds_at_once() -> None:
    document = _age(DocumentFactory.create(status="pending"), days=9)
    _analyze(document, risk=True)

    types = sorted(alert.type for alert in build_alerts(stalled_days=5))

    assert types == ["risk", "stalled"]


# -- shape --------------------------------------------------------------------------------


def test_alerts_are_ordered_newest_first() -> None:
    _age(DocumentFactory.create(status="pending", name="older"), days=30)
    _age(DocumentFactory.create(status="pending", name="newer"), days=10)

    names = [alert.document_name for alert in build_alerts(stalled_days=5)]

    assert names == ["newer", "older"]


def test_no_matching_documents_yields_an_empty_list_not_an_error() -> None:
    DocumentFactory.create(status="signed")

    assert build_alerts(stalled_days=5) == []


def test_the_threshold_falls_back_to_the_configured_default(settings) -> None:
    settings.ALERT_STALLED_DAYS = 1
    _age(DocumentFactory.create(status="pending"), days=3)

    assert len(build_alerts()) == 1
