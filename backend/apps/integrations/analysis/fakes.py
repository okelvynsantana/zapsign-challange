"""In-memory analysis provider for tests and offline runs."""

from collections.abc import Sequence

from apps.integrations.analysis.provider import (
    AnalysisProvider,
    AnalysisProviderError,
    ProviderAnalysis,
)
from apps.integrations.analysis.results import Insight

__all__ = ["FakeAnalysisProvider"]

Outcome = ProviderAnalysis | AnalysisProviderError

DEFAULT_ANALYSIS = ProviderAnalysis(
    summary="Contrato de prestação de serviços com escopo e pagamento definidos.",
    missing_topics=["foro"],
    insights=[Insight(text="Não há cláusula de confidencialidade.", risk=True)],
    model="fake-model",
)


class FakeAnalysisProvider(AnalysisProvider):
    """Returns a queued `ProviderAnalysis`, or raises a queued error."""

    def __init__(self, outcomes: Sequence[Outcome] | None = None) -> None:
        self._outcomes: list[Outcome] = list(outcomes or [])
        self.texts: list[str] = []

    def analyze(self, document_text: str) -> ProviderAnalysis:
        self.texts.append(document_text)
        outcome = self._outcomes.pop(0) if self._outcomes else DEFAULT_ANALYSIS
        if isinstance(outcome, AnalysisProviderError):
            raise outcome
        return outcome
