"""Extraction → model → regex reinforcement, returning one typed result.

Implements the pipeline rules in `contracts/analysis-provider.md` §3. It deliberately
**never raises and never touches the database**: every branch produces an `AnalysisResult`
that the caller persists. That is what makes FR-019/FR-020 hold — an analysis failure is a
recorded outcome, not an exception that could take the document down with it.
"""

from apps.integrations.analysis.clause_checker import ClauseChecker, normalize
from apps.integrations.analysis.provider import (
    AnalysisProvider,
    AnalysisProviderError,
    ProviderAnalysis,
)
from apps.integrations.analysis.results import AnalysisResult
from apps.integrations.pdf.extractor import PdfExtractionError, PdfTextExtractor

__all__ = ["AnalysisPipeline"]


class AnalysisPipeline:
    """Runs one analysis of the document behind `pdf_url`."""

    def __init__(
        self,
        extractor: PdfTextExtractor,
        provider: AnalysisProvider,
        clause_checker: ClauseChecker,
        *,
        regex_fallback_enabled: bool = True,
    ) -> None:
        self._extractor = extractor
        self._provider = provider
        self._clause_checker = clause_checker
        self._regex_fallback_enabled = regex_fallback_enabled

    def run(self, pdf_url: str) -> AnalysisResult:
        try:
            text = self._extractor.extract(pdf_url)
        except PdfExtractionError as error:
            # No text, no analysis: calling the model would only burn the time budget.
            return AnalysisResult(state="failed", source="regex", error_reason=error.kind)

        try:
            analysis = self._provider.analyze(text)
        except AnalysisProviderError as error:
            return self._without_provider(text, error)

        return self._with_provider(text, analysis)

    # -- branches ----------------------------------------------------------------------

    def _with_provider(self, text: str, analysis: ProviderAnalysis) -> AnalysisResult:
        provider_topics = list(analysis.missing_topics)
        regex_topics = self._clause_checker.missing_clauses(text)

        merged = list(provider_topics)
        added = False
        for topic in regex_topics:
            if not _already_listed(topic, merged):
                merged.append(topic)
                added = True

        return AnalysisResult(
            state="succeeded",
            summary=analysis.summary,
            missing_topics=merged,
            insights=list(analysis.insights),
            source="llm+regex" if added else "llm",
            model=analysis.model or None,
        )

    def _without_provider(self, text: str, error: AnalysisProviderError) -> AnalysisResult:
        if not self._regex_fallback_enabled:
            return AnalysisResult(
                state="failed",
                source="regex",
                error_reason=f"provider_{error.kind}",
            )

        # Degrade rather than fail: the clause checker still yields a useful answer.
        return AnalysisResult(
            state="succeeded",
            summary="",
            missing_topics=self._clause_checker.missing_clauses(text),
            insights=[],
            source="regex",
            model=None,
        )


def _already_listed(candidate: str, topics: list[str]) -> bool:
    """Whether `candidate` says the same thing as a topic the model already reported.

    Exact-string dedupe is not enough in practice: the model answers "vigência" while our
    clause label is "prazo/vigência", and a manager should not read the same missing clause
    twice under two spellings. Labels carry `/`-separated synonyms, so each alternative is
    compared on its own, accent- and case-insensitively.
    """
    existing = [normalize(topic) for topic in topics]
    alternatives = [part.strip() for part in normalize(candidate).split("/") if part.strip()]

    return any(
        alternative in seen or seen in alternative
        for alternative in alternatives
        for seen in existing
        if seen
    )
