"""PDF text extraction behind an interface (contracts/analysis-provider.md §1).

The analysis pipeline depends on `PdfTextExtractor`, never on `pypdf` or on `httpx`
(Constitution Principle I), so swapping the library — or adding OCR later — touches only
this module.

The fetch is deliberately defensive: a bounded timeout, a hard size cap enforced while
streaming (not after the body is already in memory), and a content sniff, because the URL
is supplied by a user and may point at anything at all.
"""

import io
from abc import ABC, abstractmethod
from typing import Literal

import httpx
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from apps.core.logging import log_gateway_call
from apps.integrations.config import PdfConfig

__all__ = ["PdfExtractionError", "PdfExtractionErrorKind", "PdfTextExtractor", "PypdfTextExtractor"]

PdfExtractionErrorKind = Literal["unreachable", "not_pdf", "too_large", "no_text", "timeout"]

PDF_MAGIC = b"%PDF"
CHUNK_SIZE = 64 * 1024


class PdfExtractionError(Exception):
    """Why a document's text could not be obtained; `kind` becomes the analysis reason."""

    def __init__(self, kind: PdfExtractionErrorKind, message: str) -> None:
        super().__init__(message)
        self.kind: PdfExtractionErrorKind = kind
        self.message = message

    def __str__(self) -> str:
        return f"[{self.kind}] {self.message}"


class PdfTextExtractor(ABC):
    """Turns a PDF URL into plain text."""

    @abstractmethod
    def extract(self, pdf_url: str) -> str:
        """Return the document's text. Raises `PdfExtractionError` on any failure."""


class PypdfTextExtractor(PdfTextExtractor):
    """Fetches the PDF with a bounded timeout and size cap, then extracts with `pypdf`."""

    def __init__(self, config: PdfConfig) -> None:
        self._config = config

    @log_gateway_call(provider="pdf", operation="extract")
    def extract(self, pdf_url: str) -> str:
        content = self._fetch(pdf_url)

        if not content.startswith(PDF_MAGIC):
            raise PdfExtractionError("not_pdf", "The link did not return a PDF document.")

        try:
            reader = PdfReader(io.BytesIO(content))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except (PdfReadError, ValueError, OSError) as exc:
            raise PdfExtractionError("not_pdf", f"The PDF could not be parsed: {exc}") from exc

        if not text.strip():
            # Scanned / image-only: parses fine, carries no text. OCR is out of scope.
            raise PdfExtractionError(
                "no_text", "The PDF contains no extractable text (it may be a scan)."
            )
        return text

    def _fetch(self, pdf_url: str) -> bytes:
        limit = self._config.max_bytes
        buffer = bytearray()

        try:
            with httpx.stream(
                "GET",
                pdf_url,
                timeout=self._config.fetch_timeout_seconds,
                follow_redirects=True,
            ) as response:
                if response.status_code >= httpx.codes.BAD_REQUEST:
                    raise PdfExtractionError(
                        "unreachable",
                        f"The PDF link returned HTTP {response.status_code}.",
                    )
                for chunk in response.iter_bytes(CHUNK_SIZE):
                    buffer += chunk
                    if len(buffer) > limit:
                        # Stop reading rather than buffering an unbounded body.
                        raise PdfExtractionError(
                            "too_large",
                            f"The PDF exceeds the {limit} byte limit.",
                        )
        except httpx.TimeoutException as exc:
            raise PdfExtractionError("timeout", f"Fetching the PDF timed out: {exc}") from exc
        except httpx.HTTPError as exc:
            raise PdfExtractionError("unreachable", f"The PDF link is unreachable: {exc}") from exc

        return bytes(buffer)
