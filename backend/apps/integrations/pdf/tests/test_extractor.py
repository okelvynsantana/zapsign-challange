"""T063 — `PypdfTextExtractor` (contracts/analysis-provider.md §1).

Covers every `PdfExtractionError.kind` the pipeline branches on. The HTTP fetch is mocked
with `respx`; no real PDF is ever downloaded.
"""

import io

import httpx
import pytest
import respx
from pypdf import PdfWriter

from apps.integrations.config import PdfConfig
from apps.integrations.pdf.extractor import PdfExtractionError, PypdfTextExtractor

PDF_URL = "https://files.example.test/contrato.pdf"


def _pdf_bytes(*, with_text: bool = True) -> bytes:
    """Build a minimal one-page PDF, optionally carrying extractable text."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=200, height=200)
    if with_text:
        writer.add_page(page)
        # pypdf cannot draw text, so a hand-rolled content stream supplies it.
        return _pdf_with_text("CONTRATO DE PRESTACAO DE SERVICOS")
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _pdf_with_text(text: str) -> bytes:
    """A hand-built PDF whose single page contains `text` as a real text object."""
    stream = f"BT /F1 12 Tf 20 100 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % index + body + b"\nendobj\n"
    xref_at = len(out)
    out += b"xref\n0 %d\n" % (len(objects) + 1)
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref_at,
    )
    return bytes(out)


@pytest.fixture
def extractor() -> PypdfTextExtractor:
    return PypdfTextExtractor(PdfConfig(fetch_timeout_seconds=1.0, max_bytes=1_000_000))


@respx.mock
def test_extracts_text_from_a_readable_pdf(extractor: PypdfTextExtractor) -> None:
    respx.get(PDF_URL).mock(
        return_value=httpx.Response(
            200,
            content=_pdf_with_text("CONTRATO DE PRESTACAO"),
            headers={"Content-Type": "application/pdf"},
        )
    )

    text = extractor.extract(PDF_URL)

    assert "CONTRATO" in text.upper()


@respx.mock
def test_an_unreachable_url_raises_unreachable(extractor: PypdfTextExtractor) -> None:
    respx.get(PDF_URL).mock(side_effect=httpx.ConnectError("no route"))

    with pytest.raises(PdfExtractionError) as exc_info:
        extractor.extract(PDF_URL)

    assert exc_info.value.kind == "unreachable"


@respx.mock
def test_a_404_raises_unreachable(extractor: PypdfTextExtractor) -> None:
    respx.get(PDF_URL).mock(return_value=httpx.Response(404))

    with pytest.raises(PdfExtractionError) as exc_info:
        extractor.extract(PDF_URL)

    assert exc_info.value.kind == "unreachable"


@respx.mock
def test_a_slow_fetch_raises_timeout(extractor: PypdfTextExtractor) -> None:
    respx.get(PDF_URL).mock(side_effect=httpx.ReadTimeout("too slow"))

    with pytest.raises(PdfExtractionError) as exc_info:
        extractor.extract(PDF_URL)

    assert exc_info.value.kind == "timeout"


@respx.mock
def test_a_non_pdf_body_raises_not_pdf(extractor: PypdfTextExtractor) -> None:
    respx.get(PDF_URL).mock(return_value=httpx.Response(200, content=b"<html>not a pdf</html>"))

    with pytest.raises(PdfExtractionError) as exc_info:
        extractor.extract(PDF_URL)

    assert exc_info.value.kind == "not_pdf"


@respx.mock
def test_an_oversized_pdf_raises_too_large() -> None:
    extractor = PypdfTextExtractor(PdfConfig(fetch_timeout_seconds=1.0, max_bytes=10))
    respx.get(PDF_URL).mock(return_value=httpx.Response(200, content=_pdf_with_text("CONTRATO")))

    with pytest.raises(PdfExtractionError) as exc_info:
        extractor.extract(PDF_URL)

    assert exc_info.value.kind == "too_large"


@respx.mock
def test_a_scanned_pdf_with_no_text_raises_no_text(extractor: PypdfTextExtractor) -> None:
    # An image-only PDF parses fine but yields only whitespace (spec: "no extractable text").
    respx.get(PDF_URL).mock(return_value=httpx.Response(200, content=_pdf_bytes(with_text=False)))

    with pytest.raises(PdfExtractionError) as exc_info:
        extractor.extract(PDF_URL)

    assert exc_info.value.kind == "no_text"
