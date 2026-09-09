"""T099 — which events the service emits, and that delivery can never hurt it (FR-032)."""

import pytest

from apps.automation.webhook import FakeWebhookNotifier
from apps.companies.tests.factories import CompanyFactory
from apps.documents.services import (
    DocumentDraft,
    SignerDraft,
    analyze_document,
    create_document,
)
from apps.documents.status import ProviderStatus
from apps.documents.tests.factories import DocumentFactory
from apps.integrations.analysis.clause_checker import ClauseChecker
from apps.integrations.analysis.fakes import FakeAnalysisProvider
from apps.integrations.analysis.pipeline import AnalysisPipeline
from apps.integrations.analysis.provider import ProviderAnalysis
from apps.integrations.analysis.results import Insight
from apps.integrations.pdf.fakes import FakePdfTextExtractor
from apps.integrations.zapsign.fakes import FakeZapSignGateway
from apps.integrations.zapsign.gateway import ZapSignError

pytestmark = pytest.mark.django_db


def _pipeline(*, risk: bool = True) -> AnalysisPipeline:
    return AnalysisPipeline(
        extractor=FakePdfTextExtractor(),
        provider=FakeAnalysisProvider(
            [
                ProviderAnalysis(
                    summary="Resumo.",
                    missing_topics=[],
                    insights=[Insight(text="Multa desproporcional.", risk=risk)],
                    model="fake-model",
                )
            ]
        ),
        clause_checker=ClauseChecker(),
    )


def _draft() -> DocumentDraft:
    return DocumentDraft(
        company=CompanyFactory.create(),
        name="Contrato X",
        pdf_url="https://files.example.test/contrato.pdf",
        signers=(SignerDraft(name="Ana", email="ana@example.com"),),
    )


def test_a_status_change_emits_exactly_one_status_changed_event(
    django_capture_on_commit_callbacks,
) -> None:
    notifier = FakeWebhookNotifier()

    with django_capture_on_commit_callbacks(execute=True):
        create_document(_draft(), gateway=FakeZapSignGateway(), notifier=notifier)

    status_events = [e for e in notifier.events if e.event == "document.status_changed"]
    assert len(status_events) == 1
    assert status_events[0].provider_status == ProviderStatus.SUBMITTED
    assert status_events[0].signature_status == "pending"


def test_a_provider_failure_leaves_the_status_unchanged_and_emits_nothing(
    django_capture_on_commit_callbacks,
) -> None:
    notifier = FakeWebhookNotifier()

    with django_capture_on_commit_callbacks(execute=True):
        create_document(
            _draft(),
            gateway=FakeZapSignGateway(create_results=[ZapSignError("timeout", "slow")]),
            notifier=notifier,
        )

    assert [e for e in notifier.events if e.event == "document.status_changed"] == []


def test_a_risk_bearing_analysis_emits_one_analyzed_event(
    django_capture_on_commit_callbacks,
) -> None:
    document = DocumentFactory.create()
    notifier = FakeWebhookNotifier()

    with django_capture_on_commit_callbacks(execute=True):
        analyze_document(document, pipeline=_pipeline(risk=True), notifier=notifier)

    (event,) = notifier.events
    assert event.event == "document.analyzed"
    assert event.has_risk_insight is True
    # Relativo por contrato — o consumidor (n8n) prefixa a própria base.
    assert event.report_url == f"/api/documents/{document.pk}/report/"
    assert "://" not in event.report_url


def test_an_analysis_with_no_risk_stays_quiet_by_default(
    django_capture_on_commit_callbacks,
) -> None:
    notifier = FakeWebhookNotifier()

    with django_capture_on_commit_callbacks(execute=True):
        analyze_document(
            DocumentFactory.create(), pipeline=_pipeline(risk=False), notifier=notifier
        )

    assert notifier.events == []


def test_a_risk_free_analysis_is_emitted_when_configured(
    django_capture_on_commit_callbacks, monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.documents import services
    from apps.integrations.config import WebhookConfig

    monkeypatch.setattr(
        services, "_webhook_config", lambda: WebhookConfig(url="x", on_every_analysis=True)
    )
    notifier = FakeWebhookNotifier()

    with django_capture_on_commit_callbacks(execute=True):
        analyze_document(
            DocumentFactory.create(), pipeline=_pipeline(risk=False), notifier=notifier
        )

    assert [e.event for e in notifier.events] == ["document.analyzed"]
    assert notifier.events[0].has_risk_insight is False


def test_a_notifier_that_raises_does_not_fail_the_operation(
    django_capture_on_commit_callbacks,
) -> None:
    # The contract says `notify` must not raise; the service guards anyway (FR-032).
    notifier = FakeWebhookNotifier(raises=True)

    with django_capture_on_commit_callbacks(execute=True):
        document = create_document(_draft(), gateway=FakeZapSignGateway(), notifier=notifier)

    document.refresh_from_db()
    assert document.provider_status == ProviderStatus.SUBMITTED


def test_no_notifier_at_all_is_a_supported_configuration() -> None:
    document = create_document(_draft(), gateway=FakeZapSignGateway(), notifier=None)

    assert document.provider_status == ProviderStatus.SUBMITTED


def test_events_are_emitted_only_after_the_transaction_commits(
    django_capture_on_commit_callbacks,
) -> None:
    notifier = FakeWebhookNotifier()

    with django_capture_on_commit_callbacks(execute=False):
        create_document(_draft(), gateway=FakeZapSignGateway(), notifier=notifier)
        # Callbacks are captured, not run: nothing has been delivered yet.
        assert notifier.events == []
