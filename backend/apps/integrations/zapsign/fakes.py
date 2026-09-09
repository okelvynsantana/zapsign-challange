"""In-memory ZapSign gateway for tests and offline local runs.

Queue the outcomes a scenario needs (`ZapSignCreateResult` or `ZapSignError`) and inspect
`last_create_request` afterwards. `on_create` fires *at the moment the gateway is called*,
which is how the service tests prove the local row already exists (FR-008).
"""

from collections.abc import Callable, Sequence

from apps.integrations.zapsign.gateway import (
    ZapSignCreateRequest,
    ZapSignCreateResult,
    ZapSignDocumentStatus,
    ZapSignError,
    ZapSignGateway,
)

__all__ = ["FakeZapSignGateway"]

CreateOutcome = ZapSignCreateResult | ZapSignError
StatusOutcome = ZapSignDocumentStatus | ZapSignError


def _default_result() -> ZapSignCreateResult:
    return ZapSignCreateResult(
        open_id=1,
        token="fake-doc-token",
        status="pending",
        external_id=None,
        signers=(),
    )


class FakeZapSignGateway(ZapSignGateway):
    """A scripted gateway: each call consumes the next queued outcome."""

    def __init__(
        self,
        create_results: Sequence[CreateOutcome] | None = None,
        status_results: Sequence[StatusOutcome] | None = None,
        on_create: Callable[[ZapSignCreateRequest], None] | None = None,
    ) -> None:
        self._create_results: list[CreateOutcome] = list(create_results or [])
        self._status_results: list[StatusOutcome] = list(status_results or [])
        self._on_create = on_create
        self.last_create_request: ZapSignCreateRequest | None = None
        self.create_calls = 0
        self.status_calls = 0

    def create_document(self, request: ZapSignCreateRequest) -> ZapSignCreateResult:
        self.create_calls += 1
        self.last_create_request = request
        if self._on_create is not None:
            self._on_create(request)

        outcome = self._create_results.pop(0) if self._create_results else _default_result()
        if isinstance(outcome, ZapSignError):
            raise outcome
        return outcome

    def get_document(self, *, api_token: str, doc_token: str) -> ZapSignDocumentStatus:
        self.status_calls += 1
        outcome = (
            self._status_results.pop(0)
            if self._status_results
            else ZapSignDocumentStatus(open_id=1, token=doc_token, status="pending", signers=())
        )
        if isinstance(outcome, ZapSignError):
            raise outcome
        return outcome
