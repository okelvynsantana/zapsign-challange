"""The ZapSign gateway interface every caller depends on (contracts/zapsign-gateway.md).

Models, services and views import *this* module — never `httpx`, never a ZapSign URL
(Constitution Principle I). Two implementations exist: `HttpZapSignGateway` (real) and
`FakeZapSignGateway` (tests and offline local runs).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal

__all__ = [
    "ZapSignCreateRequest",
    "ZapSignCreateResult",
    "ZapSignDocumentStatus",
    "ZapSignError",
    "ZapSignErrorKind",
    "ZapSignGateway",
    "ZapSignSignerInput",
    "ZapSignSignerResult",
]

ZapSignErrorKind = Literal["timeout", "connection", "http_status", "invalid_response", "auth"]


@dataclass(frozen=True, slots=True)
class ZapSignSignerInput:
    """A signer as we send it to ZapSign."""

    name: str
    email: str


@dataclass(frozen=True, slots=True)
class ZapSignCreateRequest:
    """Everything one document submission needs.

    `api_token` is passed in per call — it belongs to the owning `Company` row and is
    never read from global configuration.
    """

    api_token: str
    name: str
    pdf_url: str
    signers: tuple[ZapSignSignerInput, ...]
    external_id: str | None = None


@dataclass(frozen=True, slots=True)
class ZapSignSignerResult:
    """A signer as ZapSign reports it back."""

    name: str
    email: str
    token: str | None
    status: str | None
    external_id: str | None


@dataclass(frozen=True, slots=True)
class ZapSignCreateResult:
    """The provider's answer to a successful document creation."""

    open_id: int
    token: str
    status: str
    external_id: str | None
    signers: tuple[ZapSignSignerResult, ...] = field(default=())


@dataclass(frozen=True, slots=True)
class ZapSignDocumentStatus:
    """The provider's current view of a document we already created."""

    open_id: int
    token: str
    status: str
    signers: tuple[ZapSignSignerResult, ...] = field(default=())


class ZapSignError(Exception):
    """The single failure type callers handle — never a raw `httpx` exception.

    `message` is safe to log and to store in `Document.last_provider_error`: the gateway
    redacts the API token before constructing it.
    """

    def __init__(
        self,
        kind: ZapSignErrorKind,
        message: str,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.kind: ZapSignErrorKind = kind
        self.message = message
        self.status_code = status_code

    def __str__(self) -> str:
        suffix = f" (status {self.status_code})" if self.status_code else ""
        return f"[{self.kind}] {self.message}{suffix}"


class ZapSignGateway(ABC):
    """Synchronous ZapSign access, bounded by the configured timeouts."""

    @abstractmethod
    def create_document(self, request: ZapSignCreateRequest) -> ZapSignCreateResult:
        """Create a document for signature. Raises `ZapSignError` on any failure."""

    @abstractmethod
    def get_document(self, *, api_token: str, doc_token: str) -> ZapSignDocumentStatus:
        """Fetch the provider's current status. Raises `ZapSignError` on any failure."""
