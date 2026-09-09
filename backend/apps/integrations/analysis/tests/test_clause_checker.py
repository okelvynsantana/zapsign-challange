"""T065 — the regex clause reinforcement pass (research.md §6)."""

from apps.integrations.analysis.clause_checker import DEFAULT_CLAUSE_PATTERNS, ClauseChecker

FULL_CONTRACT = """
CLÁUSULA PRIMEIRA - DO OBJETO: prestação de serviços de desenvolvimento.
CLÁUSULA SEGUNDA - DO PAGAMENTO: R$ 10.000,00 mensais.
CLÁUSULA TERCEIRA - DA VIGÊNCIA: 12 meses a contar da assinatura.
CLÁUSULA QUARTA - DA RESCISÃO: mediante aviso prévio de 30 dias.
CLÁUSULA QUINTA - DA MULTA: 10% sobre o valor remanescente.
CLÁUSULA SEXTA - DA CONFIDENCIALIDADE: as partes obrigam-se ao sigilo.
CLÁUSULA SÉTIMA - DA PROTEÇÃO DE DADOS: observância da LGPD.
CLÁUSULA OITAVA - DO FORO: comarca de São Paulo.
"""


def test_a_complete_contract_reports_nothing_missing() -> None:
    assert ClauseChecker().missing_clauses(FULL_CONTRACT) == []


def test_absent_clauses_are_reported_by_label() -> None:
    text = "CLÁUSULA PRIMEIRA - DO OBJETO: prestação de serviços."

    missing = ClauseChecker().missing_clauses(text)

    assert "foro" in missing
    assert "rescisão" in missing
    assert "objeto" not in missing


def test_matching_ignores_case_and_accents_are_matched_as_written() -> None:
    checker = ClauseChecker({"rescisão": ["rescis"]})

    assert checker.missing_clauses("A RESCISÃO ocorrerá...") == []


def test_the_clause_set_is_overridable() -> None:
    checker = ClauseChecker({"garantia": ["garantia", "warranty"]})

    assert checker.missing_clauses("sem nada aqui") == ["garantia"]
    assert checker.missing_clauses("há uma garantia de 90 dias") == []


def test_empty_text_reports_every_expected_clause() -> None:
    assert ClauseChecker().missing_clauses("") == list(DEFAULT_CLAUSE_PATTERNS)


def test_labels_keep_their_declared_order() -> None:
    missing = ClauseChecker().missing_clauses("")

    assert missing == [label for label in DEFAULT_CLAUSE_PATTERNS if label in missing]
