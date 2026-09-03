"""The typed result the analysis pipeline produces.

Lives in `integrations/` because it is what a *provider pipeline* returns, not a
persistence concern: `apps.documents` turns one of these into a `DocumentAnalysis` row.
Frozen and plain, so pipeline behaviour can be asserted without a database.
"""

from dataclasses import dataclass, field
from typing import Literal

__all__ = ["AnalysisResult", "AnalysisSource", "AnalysisState", "Insight"]

AnalysisState = Literal["succeeded", "failed"]
AnalysisSource = Literal["llm", "regex", "llm+regex"]


@dataclass(frozen=True, slots=True)
class Insight:
    """One observation about the document. `risk` drives the alerts and the webhook."""

    text: str
    risk: bool = False


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """The outcome of one analysis run, ready to be persisted."""

    state: AnalysisState
    summary: str = ""
    missing_topics: list[str] = field(default_factory=list)
    insights: list[Insight] = field(default_factory=list)
    source: AnalysisSource = "regex"
    model: str | None = None
    error_reason: str = ""

    @property
    def has_risk_insight(self) -> bool:
        """Whether this run flagged anything risk-related (FR-030, FR-031)."""
        return self.state == "succeeded" and any(insight.risk for insight in self.insights)
