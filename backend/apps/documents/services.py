"""Use cases that span several models *and* an external call.

These three are the only operations that earn a service (plan.md, Principle III): they
write more than one table and then talk to a provider. Single-model CRUD goes straight
through the viewset and serializer.

Shape of every function here: plain, typed, and given its gateway by the caller — nothing
resolves a provider from global state, so a test passes a fake and needs no patching.

The ordering is the resilience rule (Principle IV, FR-008): the local rows are committed
first, the outbound call happens second, and its outcome is folded back in. A provider
failure therefore *never* costs us the document.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass

from django.db import transaction

from apps.automation.webhook import (
    WebhookNotifier,
    build_analyzed_event,
    build_status_changed_event,
)
from apps.companies.models import Company
from apps.core.exceptions import ConflictError
from apps.documents.models import Document, DocumentAnalysis
from apps.documents.status import ProviderStatus
from apps.integrations.analysis.pipeline import AnalysisPipeline
from apps.integrations.analysis.results import AnalysisResult
from apps.integrations.config import WebhookConfig, get_integrations_config
from apps.integrations.zapsign.gateway import (
    ZapSignCreateRequest,
    ZapSignCreateResult,
    ZapSignDocumentStatus,
    ZapSignError,
    ZapSignGateway,
    ZapSignSignerInput,
)
from apps.signers.models import Signer

logger = logging.getLogger("integrations.webhook")

__all__ = [
    "DocumentDraft",
    "SignerDraft",
    "analyze_document",
    "create_document",
    "resync_document",
]


@dataclass(frozen=True, slots=True)
class SignerDraft:
    """A signer as the caller supplied them, before any row exists."""

    name: str
    email: str


@dataclass(frozen=True, slots=True)
class DocumentDraft:
    """Validated input for one document creation, from the SPA or from automation."""

    company: Company
    name: str
    pdf_url: str
    signers: tuple[SignerDraft, ...]
    external_id: str | None = None
    created_by: str = ""


def create_document(
    draft: DocumentDraft,
    *,
    gateway: ZapSignGateway,
    pipeline: AnalysisPipeline | None = None,
    notifier: WebhookNotifier | None = None,
) -> Document:
    """Persist the document and its signers, submit them to ZapSign, then analyze.

    Returns the document whatever happens downstream: `submitted` with the provider's
    identifiers, or `failed` with a readable reason and a retry available through
    `resync_document` (FR-008, FR-009, FR-010).

    The analysis runs last and cannot affect either of the earlier steps (FR-020): a
    failing pipeline records a `failed` analysis row and nothing more.
    """
    document = _persist(draft)

    previous_status = document.status
    _submit(document, gateway=gateway)
    _emit_status_change(document, previous_status, notifier)

    if pipeline is not None:
        analyze_document(document, pipeline=pipeline, notifier=notifier)
    return document


def analyze_document(
    document: Document,
    *,
    pipeline: AnalysisPipeline,
    notifier: WebhookNotifier | None = None,
) -> DocumentAnalysis:
    """Run the analysis pipeline and store the outcome as a **new** row.

    Never updates an earlier analysis and never touches the document's provider fields
    (FR-017, FR-019, FR-020). The pipeline itself does not raise, so both a successful and
    a failed run end up recorded and retryable.
    """
    result = pipeline.run(document.pdf_url)
    analysis = _persist_analysis(document, result)
    _emit_analyzed(document, analysis, notifier)
    return analysis


def resync_document(
    document: Document,
    *,
    gateway: ZapSignGateway,
    notifier: WebhookNotifier | None = None,
) -> Document:
    """Re-submit a failed document, or refresh a submitted one from the provider.

    Raises `ConflictError` when an attempt is still in flight — re-triggering then would
    double-submit the document.
    """
    if not document.can_resync():
        raise ConflictError(
            detail="This document cannot be resynchronised in its current state.",
            code="resync_not_allowed",
        )

    previous_status = document.status
    if document.provider_status == ProviderStatus.SUBMITTED and document.token:
        _refresh(document, gateway=gateway)
    else:
        _submit(document, gateway=gateway)

    _emit_status_change(document, previous_status, notifier)
    return document


# -- internals -------------------------------------------------------------------------


@transaction.atomic
def _persist(draft: DocumentDraft) -> Document:
    """Write the document and its signers in one transaction, before any outbound call."""
    document = Document.objects.create(
        company=draft.company,
        name=draft.name,
        pdf_url=draft.pdf_url,
        external_id=draft.external_id or "",
        created_by=draft.created_by,
        provider_status=ProviderStatus.PENDING_INTEGRATION,
    )
    Signer.objects.bulk_create(
        Signer(document=document, name=signer.name, email=signer.email.strip().lower())
        for signer in draft.signers
    )
    return document


def _submit(document: Document, *, gateway: ZapSignGateway) -> None:
    """Send the document to ZapSign and record the outcome on the row."""
    request = ZapSignCreateRequest(
        api_token=document.company.api_token,
        name=document.name,
        pdf_url=document.pdf_url,
        signers=tuple(
            ZapSignSignerInput(name=signer.name, email=signer.email)
            for signer in document.signers.all()
        ),
        external_id=document.external_id or None,
    )

    try:
        result = gateway.create_document(request)
    except ZapSignError as error:
        document.mark_provider_failed(str(error))
    else:
        document.mark_submitted(result)
        _apply_signer_results(document, result)

    document.save()


def _refresh(document: Document, *, gateway: ZapSignGateway) -> None:
    """Pull the provider's current signature status onto the row."""
    try:
        result = gateway.get_document(
            api_token=document.company.api_token,
            doc_token=document.token,
        )
    except ZapSignError as error:
        document.mark_provider_failed(str(error))
    else:
        document.mark_submitted(result)
        _apply_signer_results(document, result)

    document.save()


def _apply_signer_results(
    document: Document,
    result: ZapSignCreateResult | ZapSignDocumentStatus,
) -> None:
    """Copy per-signer tokens and statuses back, matched by email (gateway contract)."""
    by_email = {signer.email.strip().lower(): signer for signer in result.signers}
    if not by_email:
        return

    updated: list[Signer] = []
    for signer in document.signers.all():
        provider_signer = by_email.get(signer.email)
        if provider_signer is None:
            continue
        signer.token = provider_signer.token or ""
        signer.status = provider_signer.status or ""
        if provider_signer.external_id:
            signer.external_id = provider_signer.external_id
        updated.append(signer)

    if updated:
        Signer.objects.bulk_update(updated, ["token", "status", "external_id"])


def _persist_analysis(document: Document, result: AnalysisResult) -> DocumentAnalysis:
    """Insert one `DocumentAnalysis` from a pipeline result. Insert-only, by design."""
    return DocumentAnalysis.objects.create(
        document=document,
        state=result.state,
        summary=result.summary,
        missing_topics=list(result.missing_topics),
        insights=[{"text": insight.text, "risk": insight.risk} for insight in result.insights],
        source=result.source,
        error_reason=result.error_reason,
        model=result.model or "",
    )


# -- outbound events (bonus — User Story 6) ----------------------------------------------


def _emit_status_change(
    document: Document,
    previous_status: str,
    notifier: WebhookNotifier | None,
) -> None:
    """Emit `document.status_changed`, but only when the status actually moved."""
    if notifier is None or document.status == previous_status:
        return
    _emit(notifier, lambda: build_status_changed_event(document))


def _emit_analyzed(
    document: Document,
    analysis: DocumentAnalysis,
    notifier: WebhookNotifier | None,
) -> None:
    """Emit `document.analyzed`; risk-free runs only when explicitly configured."""
    if notifier is None:
        return
    if not analysis.has_risk_insight and not _webhook_config().on_every_analysis:
        return
    _emit(notifier, lambda: build_analyzed_event(document))


def _emit(notifier: WebhookNotifier, build: Callable[[], object]) -> None:
    """Deliver after the surrounding transaction commits, and never let it propagate.

    The notifier contract already says `notify` must not raise; this guard is belt and
    braces, because a webhook must never be able to roll back a document (FR-032).
    """

    def send() -> None:
        try:
            notifier.notify(build())  # type: ignore[arg-type]
        except Exception:
            logger.exception("webhook_emit_failed")

    transaction.on_commit(send)


def _webhook_config() -> WebhookConfig:
    return get_integrations_config().webhook
