"""T041 — `Document` status rules (US2: FR-009, FR-010, FR-013).

Status handling is business logic, so it lives on the model and in a pure helper module
rather than in a view. TDD-critical per the constitution.
"""

import pytest

from apps.documents.models import Document
from apps.documents.status import ProviderStatus, can_resync
from apps.integrations.zapsign.gateway import (
    ZapSignCreateResult,
    ZapSignSignerResult,
)


def _result() -> ZapSignCreateResult:
    return ZapSignCreateResult(
        open_id=99,
        token="doc-token",
        status="pending",
        external_id="ref",
        signers=(
            ZapSignSignerResult(
                name="Ana",
                email="ana@example.com",
                token="signer-token",
                status="new",
                external_id=None,
            ),
        ),
    )


def test_a_new_document_starts_pending_integration() -> None:
    assert Document().provider_status == ProviderStatus.PENDING_INTEGRATION


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (ProviderStatus.PENDING_INTEGRATION, False),
        (ProviderStatus.SUBMITTED, True),
        (ProviderStatus.FAILED, True),
    ],
)
def test_resync_is_allowed_only_from_a_settled_state(
    status: ProviderStatus, expected: bool
) -> None:
    # An attempt still in flight (`pending_integration`) is not re-triggerable.
    assert can_resync(status) is expected
    assert Document(provider_status=status).can_resync() is expected


def test_mark_submitted_copies_the_provider_fields_across() -> None:
    document = Document(provider_status=ProviderStatus.FAILED, last_provider_error="earlier boom")

    document.mark_submitted(_result())

    assert document.provider_status == ProviderStatus.SUBMITTED
    assert document.open_id == 99
    assert document.token == "doc-token"
    assert document.status == "pending"
    assert document.last_provider_error == ""


def test_mark_provider_failed_records_a_retryable_state_and_the_reason() -> None:
    document = Document(provider_status=ProviderStatus.PENDING_INTEGRATION)

    document.mark_provider_failed("timeout talking to ZapSign")

    assert document.provider_status == ProviderStatus.FAILED
    assert document.last_provider_error == "timeout talking to ZapSign"
    assert document.can_resync() is True


def test_the_signature_status_is_never_computed_locally() -> None:
    # `status` mirrors whatever ZapSign reports; we only store and display it (FR-013).
    document = Document()
    document.mark_submitted(_result())

    assert document.status == "pending"
