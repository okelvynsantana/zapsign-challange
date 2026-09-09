"""T042 — `create_document` local-first write and ZapSign mapping.

The rule this pins is Constitution Principle IV / FR-008: the local row exists *before*
any outbound call, so a provider outage can never lose a document.
"""

import pytest

from apps.companies.tests.factories import CompanyFactory
from apps.documents.models import Document
from apps.documents.services import DocumentDraft, SignerDraft, create_document
from apps.documents.status import ProviderStatus
from apps.integrations.zapsign.fakes import FakeZapSignGateway
from apps.integrations.zapsign.gateway import (
    ZapSignCreateResult,
    ZapSignError,
    ZapSignSignerResult,
)
from apps.signers.models import Signer

pytestmark = pytest.mark.django_db


def _draft(company=None) -> DocumentDraft:
    return DocumentDraft(
        company=company or CompanyFactory.create(),
        name="Contrato de Prestação de Serviços",
        pdf_url="https://files.example.test/contrato.pdf",
        signers=(
            SignerDraft(name="Ana Souza", email="ana@example.com"),
            SignerDraft(name="Bruno Lima", email="bruno@example.com"),
        ),
        external_id="ref-1",
        created_by="manager",
    )


def _success(external_id: str | None = "ref-1") -> ZapSignCreateResult:
    return ZapSignCreateResult(
        open_id=123456,
        token="zapsign-doc-token",
        status="pending",
        external_id=external_id,
        signers=(
            ZapSignSignerResult(
                name="Ana Souza",
                email="ana@example.com",
                token="signer-token-a",
                status="new",
                external_id=None,
            ),
            ZapSignSignerResult(
                name="Bruno Lima",
                email="bruno@example.com",
                token="signer-token-b",
                status="new",
                external_id=None,
            ),
        ),
    )


def test_the_document_and_signers_exist_before_the_gateway_is_called() -> None:
    seen: dict[str, int] = {}
    gateway = FakeZapSignGateway(
        create_results=[_success()],
        on_create=lambda _request: seen.update(
            documents=Document.objects.count(), signers=Signer.objects.count()
        ),
    )

    create_document(_draft(), gateway=gateway)

    assert seen == {"documents": 1, "signers": 2}


def test_a_successful_submission_stores_the_provider_identifiers() -> None:
    gateway = FakeZapSignGateway(create_results=[_success()])

    document = create_document(_draft(), gateway=gateway)

    assert document.provider_status == ProviderStatus.SUBMITTED
    assert document.open_id == 123456
    assert document.token == "zapsign-doc-token"
    assert document.status == "pending"
    assert document.last_provider_error == ""


def test_signer_tokens_are_matched_back_by_email() -> None:
    gateway = FakeZapSignGateway(create_results=[_success()])

    document = create_document(_draft(), gateway=gateway)

    tokens = {s.email: s.token for s in document.signers.all()}
    assert tokens == {"ana@example.com": "signer-token-a", "bruno@example.com": "signer-token-b"}


def test_the_company_credential_is_what_reaches_the_gateway() -> None:
    company = CompanyFactory.create(api_token="company-specific-token")
    gateway = FakeZapSignGateway(create_results=[_success()])

    create_document(_draft(company), gateway=gateway)

    assert gateway.last_create_request is not None
    assert gateway.last_create_request.api_token == "company-specific-token"


def test_a_provider_failure_keeps_the_document_in_a_retryable_state() -> None:
    gateway = FakeZapSignGateway(create_results=[ZapSignError(kind="timeout", message="too slow")])

    document = create_document(_draft(), gateway=gateway)

    assert document.provider_status == ProviderStatus.FAILED
    assert "too slow" in document.last_provider_error
    assert document.can_resync() is True
    assert Document.objects.count() == 1
    assert Signer.objects.count() == 2


def test_a_provider_failure_does_not_roll_back_the_local_write() -> None:
    gateway = FakeZapSignGateway(
        create_results=[ZapSignError(kind="http_status", status_code=500, message="boom")]
    )

    document = create_document(_draft(), gateway=gateway)
    document.refresh_from_db()

    assert document.pk is not None
    assert document.provider_status == ProviderStatus.FAILED


def test_resync_recovers_a_failed_document() -> None:
    from apps.documents.services import resync_document

    gateway = FakeZapSignGateway(
        create_results=[ZapSignError(kind="timeout", message="too slow")],
        status_results=[],
    )
    document = create_document(_draft(), gateway=gateway)

    recovered = resync_document(document, gateway=FakeZapSignGateway(create_results=[_success()]))

    assert recovered.provider_status == ProviderStatus.SUBMITTED
    assert recovered.token == "zapsign-doc-token"


def test_resync_of_a_submitted_document_refreshes_the_signature_status() -> None:
    from apps.documents.services import resync_document
    from apps.integrations.zapsign.gateway import ZapSignDocumentStatus

    document = create_document(_draft(), gateway=FakeZapSignGateway(create_results=[_success()]))
    refresher = FakeZapSignGateway(
        status_results=[
            ZapSignDocumentStatus(
                open_id=123456,
                token="zapsign-doc-token",
                status="signed",
                signers=(
                    ZapSignSignerResult(
                        name="Ana Souza",
                        email="ana@example.com",
                        token="signer-token-a",
                        status="signed",
                        external_id=None,
                    ),
                ),
            )
        ]
    )

    refreshed = resync_document(document, gateway=refresher)

    assert refreshed.status == "signed"
    assert refreshed.signers.get(email="ana@example.com").status == "signed"
