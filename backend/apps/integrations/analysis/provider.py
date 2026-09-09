"""The AI analysis provider interface (contracts/analysis-provider.md §2).

The pipeline depends on this ABC, never on the `openai` SDK (Constitution Principle I),
which is what keeps a future move to asynchronous processing a caller-side change.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal

from apps.integrations.analysis.results import Insight

__all__ = [
    "AnalysisProvider",
    "AnalysisProviderError",
    "AnalysisProviderErrorKind",
    "ProviderAnalysis",
]

AnalysisProviderErrorKind = Literal[
    "timeout", "connection", "rate_limit", "http_status", "invalid_response", "auth"
]


@dataclass(frozen=True, slots=True)
class ProviderAnalysis:
    """What the model returned, before the regex pass merges into it."""

    summary: str
    missing_topics: list[str] = field(default_factory=list)
    insights: list[Insight] = field(default_factory=list)
    model: str = ""


class AnalysisProviderError(Exception):
    """The single failure type the pipeline handles — never a raw SDK exception."""

    def __init__(
        self,
        kind: AnalysisProviderErrorKind,
        message: str,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.kind: AnalysisProviderErrorKind = kind
        self.message = message
        self.status_code = status_code

    def __str__(self) -> str:
        return f"[{self.kind}] {self.message}"


class AnalysisProvider(ABC):
    """Turns document text into a structured analysis, within a bounded time budget."""

    @abstractmethod
    def analyze(self, document_text: str) -> ProviderAnalysis:
        """Analyze the text. Raises `AnalysisProviderError` on any failure."""
