"""`deploy/.env.example` must stay parseable by Docker Compose.

Compose strips a trailing `# comment` only when a value precedes it. For a **blank** value
(`KEY=            # explanation`) it takes the comment text as the value — so a
"blank means off" setting silently switches on, holding nonsense. That bug shipped once
and was only caught by running the container stack; this pins it.
"""

import re

from django.conf import settings

ENV_EXAMPLE = settings.BASE_DIR.parent / "deploy" / ".env.example"

ASSIGNMENT = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>.*)$")


def _assignments() -> list[tuple[int, str, str]]:
    rows = []
    for number, line in enumerate(ENV_EXAMPLE.read_text().splitlines(), start=1):
        match = ASSIGNMENT.match(line)
        if match:
            rows.append((number, match["key"], match["value"]))
    return rows


def test_the_example_file_exists_and_declares_variables() -> None:
    assert ENV_EXAMPLE.is_file()
    assert len(_assignments()) > 20


def test_no_assignment_carries_a_trailing_inline_comment() -> None:
    offenders = [
        f"{ENV_EXAMPLE.name}:{number}: {key}"
        for number, key, value in _assignments()
        if "#" in value
    ]

    assert offenders == [], (
        "Move these comments onto their own line — Compose folds a trailing comment into "
        f"an empty value: {offenders}"
    )


def test_secrets_are_left_blank_rather_than_pre_filled() -> None:
    values = {key: value for _, key, value in _assignments()}

    assert values["DJANGO_SECRET_KEY"] == ""
    assert values["SEED_PASSWORD"] == ""
    assert values["OPENAI_API_KEY"] == ""


def test_the_optional_webhook_is_off_by_default() -> None:
    values = {key: value for _, key, value in _assignments()}

    # A non-empty URL here turns the outbound webhook on for every fresh install.
    assert values["N8N_WEBHOOK_URL"] == ""
    assert values["N8N_WEBHOOK_SECRET"] == ""


def test_every_variable_the_settings_read_is_documented() -> None:
    documented = {key for _, key, _ in _assignments()}
    required = {
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "DJANGO_SECRET_KEY",
        "DJANGO_SETTINGS_MODULE",
        "DJANGO_DEBUG",
        "DJANGO_ALLOWED_HOSTS",
        "DJANGO_CORS_ALLOWED_ORIGINS",
        "SEED_USERNAME",
        "SEED_PASSWORD",
        "ZAPSIGN_BASE_URL",
        "ZAPSIGN_TIMEOUT_SECONDS",
        "ZAPSIGN_VERIFY_SSL",
        "ZAPSIGN_USE_FAKE",
        "OPENAI_API_KEY",
        "AI_MODEL",
        "AI_TIMEOUT_SECONDS",
        "AI_MAX_INPUT_CHARS",
        "AI_REGEX_FALLBACK_ENABLED",
        "AI_EXPECTED_CLAUSES",
        "AI_USE_FAKE",
        "PDF_FETCH_TIMEOUT_SECONDS",
        "PDF_MAX_BYTES",
        "ALERT_STALLED_DAYS",
        "N8N_WEBHOOK_URL",
        "N8N_WEBHOOK_SECRET",
        "WEBHOOK_TIMEOUT_SECONDS",
        "WEBHOOK_ON_EVERY_ANALYSIS",
    }

    assert required - documented == set()
