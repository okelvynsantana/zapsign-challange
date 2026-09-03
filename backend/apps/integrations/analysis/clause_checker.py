"""Regex reinforcement for the missing-clause list (research.md §6).

An independent second opinion on completeness: it does not depend on the model
"remembering" to check everything, and it is what still produces a useful answer when the
LLM is unavailable (the pipeline's regex fallback).
"""

import re
import unicodedata
from collections.abc import Mapping, Sequence

__all__ = ["DEFAULT_CLAUSE_PATTERNS", "ClauseChecker", "normalize"]

#: Label -> substrings that indicate the clause is present. Ordered: the reported list
#: keeps this order so output is stable between runs.
DEFAULT_CLAUSE_PATTERNS: Mapping[str, Sequence[str]] = {
    "objeto": ["objeto"],
    "prazo/vigência": ["vigencia", "prazo", "duracao"],
    "rescisão": ["rescis", "resilic", "distrato"],
    "multa/penalidade": ["multa", "penalidade", "clausula penal"],
    "foro": ["foro", "comarca", "jurisdic"],
    "confidencialidade": ["confidencial", "sigilo", "nao divulgac"],
    "pagamento": ["pagamento", "remunerac", "preco"],
    "proteção de dados/LGPD": ["lgpd", "protecao de dados", "dados pessoais"],
}


def normalize(text: str) -> str:
    """Case-fold and strip accents so `RESCISÃO` matches the pattern `rescis`."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


class ClauseChecker:
    """Reports which expected clauses appear to be absent from a contract."""

    def __init__(self, clauses: Mapping[str, Sequence[str]] | None = None) -> None:
        self._clauses = dict(clauses or DEFAULT_CLAUSE_PATTERNS)

    def missing_clauses(self, text: str) -> list[str]:
        """Return the labels whose patterns are all absent, in declaration order."""
        normalized = normalize(text)
        return [
            label
            for label, patterns in self._clauses.items()
            if not any(re.search(re.escape(normalize(p)), normalized) for p in patterns)
        ]
