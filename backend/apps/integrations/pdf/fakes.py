"""In-memory PDF extractor for tests and offline runs."""

from collections.abc import Sequence

from apps.integrations.pdf.extractor import PdfExtractionError, PdfTextExtractor

__all__ = ["FakePdfTextExtractor"]

Outcome = str | PdfExtractionError

DEFAULT_TEXT = (
    "CONTRATO DE PRESTAÇÃO DE SERVIÇOS\nObjeto: desenvolvimento de software.\nPagamento: mensal.\n"
)


class FakePdfTextExtractor(PdfTextExtractor):
    """Returns queued text, or raises a queued `PdfExtractionError`."""

    def __init__(self, outcomes: Sequence[Outcome] | None = None) -> None:
        self._outcomes: list[Outcome] = list(outcomes or [])
        self.calls: list[str] = []

    def extract(self, pdf_url: str) -> str:
        self.calls.append(pdf_url)
        outcome = self._outcomes.pop(0) if self._outcomes else DEFAULT_TEXT
        if isinstance(outcome, PdfExtractionError):
            raise outcome
        return outcome
