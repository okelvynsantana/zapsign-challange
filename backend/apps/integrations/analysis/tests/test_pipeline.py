"""T066 — `AnalysisPipeline` branch coverage (contracts/analysis-provider.md §3).

Every rule in the contract's pipeline section is pinned here, driven entirely by fakes:
extraction failures short-circuit, the regex pass reinforces the model's answer, and the
regex fallback is what keeps a provider outage from costing the user an analysis.
"""

import pytest

from apps.integrations.analysis.clause_checker import ClauseChecker
from apps.integrations.analysis.fakes import FakeAnalysisProvider
from apps.integrations.analysis.pipeline import AnalysisPipeline
from apps.integrations.analysis.provider import AnalysisProviderError, ProviderAnalysis
from apps.integrations.analysis.results import Insight
from apps.integrations.pdf.extractor import PdfExtractionError
from apps.integrations.pdf.fakes import FakePdfTextExtractor

PDF_URL = "https://files.example.test/contrato.pdf"

COMPLETE_TEXT = (
    "OBJETO: serviços. PAGAMENTO: mensal. VIGÊNCIA: 12 meses. RESCISÃO: aviso prévio. "
    "MULTA: 10%. FORO: São Paulo. CONFIDENCIALIDADE: sigilo. LGPD: dados pessoais."
)
TEXT_WITHOUT_FORO = COMPLETE_TEXT.replace("FORO: São Paulo. ", "")


def _pipeline(
    extractor: FakePdfTextExtractor,
    provider: FakeAnalysisProvider,
    *,
    regex_fallback_enabled: bool = True,
) -> AnalysisPipeline:
    return AnalysisPipeline(
        extractor=extractor,
        provider=provider,
        clause_checker=ClauseChecker(),
        regex_fallback_enabled=regex_fallback_enabled,
    )


def test_no_extractable_text_fails_without_calling_the_provider() -> None:
    provider = FakeAnalysisProvider()
    pipeline = _pipeline(FakePdfTextExtractor([PdfExtractionError("no_text", "scanned")]), provider)

    result = pipeline.run(PDF_URL)

    assert result.state == "failed"
    assert result.error_reason == "no_text"
    assert provider.texts == []


@pytest.mark.parametrize("kind", ["unreachable", "not_pdf", "too_large", "timeout"])
def test_every_extraction_failure_becomes_its_reason(kind: str) -> None:
    pipeline = _pipeline(
        FakePdfTextExtractor([PdfExtractionError(kind, "nope")]),  # type: ignore[arg-type]
        FakeAnalysisProvider(),
    )

    result = pipeline.run(PDF_URL)

    assert (result.state, result.error_reason) == ("failed", kind)


def test_a_model_answer_with_nothing_left_to_add_is_sourced_llm() -> None:
    provider = FakeAnalysisProvider(
        [ProviderAnalysis(summary="Resumo.", missing_topics=[], insights=[], model="gpt-4o-mini")]
    )
    pipeline = _pipeline(FakePdfTextExtractor([COMPLETE_TEXT]), provider)

    result = pipeline.run(PDF_URL)

    assert result.state == "succeeded"
    assert result.source == "llm"
    assert result.summary == "Resumo."
    assert result.model == "gpt-4o-mini"
    assert result.missing_topics == []


def test_the_regex_pass_adds_a_clause_the_model_missed() -> None:
    provider = FakeAnalysisProvider(
        [ProviderAnalysis(summary="Resumo.", missing_topics=[], insights=[], model="gpt-4o-mini")]
    )
    pipeline = _pipeline(FakePdfTextExtractor([TEXT_WITHOUT_FORO]), provider)

    result = pipeline.run(PDF_URL)

    assert result.source == "llm+regex"
    assert "foro" in result.missing_topics


def test_a_clause_both_sides_found_is_listed_exactly_once() -> None:
    provider = FakeAnalysisProvider(
        [ProviderAnalysis(summary="Resumo.", missing_topics=["foro"], insights=[], model="m")]
    )
    pipeline = _pipeline(FakePdfTextExtractor([TEXT_WITHOUT_FORO]), provider)

    result = pipeline.run(PDF_URL)

    assert result.missing_topics.count("foro") == 1
    assert result.source == "llm"  # the checker added nothing new


def test_risk_insights_survive_the_merge() -> None:
    provider = FakeAnalysisProvider(
        [
            ProviderAnalysis(
                summary="Resumo.",
                missing_topics=[],
                insights=[Insight(text="Multa desproporcional.", risk=True)],
                model="m",
            )
        ]
    )
    pipeline = _pipeline(FakePdfTextExtractor([COMPLETE_TEXT]), provider)

    result = pipeline.run(PDF_URL)

    assert [i.risk for i in result.insights] == [True]
    assert result.has_risk_insight is True


def test_a_clause_the_model_named_differently_is_not_listed_twice() -> None:
    """Real output regression: the model says "vigência", our label is "prazo/vigência"."""
    provider = FakeAnalysisProvider(
        [
            ProviderAnalysis(
                summary="Resumo.",
                missing_topics=["vigência", "multa", "proteção de dados"],
                insights=[],
                model="gpt-4o-mini",
            )
        ]
    )
    pipeline = _pipeline(FakePdfTextExtractor(["texto sem nenhuma clausula"]), provider)

    topics = pipeline.run(PDF_URL).missing_topics

    assert "prazo/vigência" not in topics
    assert "multa/penalidade" not in topics
    assert "proteção de dados/LGPD" not in topics
    assert topics[:3] == ["vigência", "multa", "proteção de dados"]
    # As que o modelo realmente não citou continuam entrando.
    assert "foro" in topics
    assert "objeto" in topics


def test_accents_and_case_do_not_defeat_the_dedupe() -> None:
    provider = FakeAnalysisProvider(
        [
            ProviderAnalysis(
                summary="R.", missing_topics=["RESCISAO", "Foro"], insights=[], model="m"
            )
        ]
    )
    pipeline = _pipeline(FakePdfTextExtractor(["texto vazio"]), provider)

    topics = pipeline.run(PDF_URL).missing_topics

    assert topics.count("rescisão") == 0
    assert topics.count("foro") == 0
    assert "RESCISAO" in topics and "Foro" in topics


def test_a_provider_timeout_falls_back_to_the_regex_pass() -> None:
    provider = FakeAnalysisProvider([AnalysisProviderError("timeout", "too slow")])
    pipeline = _pipeline(FakePdfTextExtractor([TEXT_WITHOUT_FORO]), provider)

    result = pipeline.run(PDF_URL)

    assert result.state == "succeeded"
    assert result.source == "regex"
    assert result.summary == ""
    assert result.model is None
    assert "foro" in result.missing_topics


def test_with_the_fallback_disabled_a_provider_timeout_fails() -> None:
    provider = FakeAnalysisProvider([AnalysisProviderError("timeout", "too slow")])
    pipeline = _pipeline(
        FakePdfTextExtractor([COMPLETE_TEXT]), provider, regex_fallback_enabled=False
    )

    result = pipeline.run(PDF_URL)

    assert result.state == "failed"
    assert result.error_reason == "provider_timeout"
    assert result.source == "regex"


def test_the_pipeline_never_touches_the_database_or_raises() -> None:
    # It returns a result for every branch — persistence is the caller's job.
    provider = FakeAnalysisProvider([AnalysisProviderError("auth", "bad key")])
    pipeline = _pipeline(
        FakePdfTextExtractor([COMPLETE_TEXT]), provider, regex_fallback_enabled=False
    )

    result = pipeline.run(PDF_URL)

    assert result.error_reason == "provider_auth"
