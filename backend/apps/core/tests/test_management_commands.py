"""Coverage for the operator-facing commands the quickstart and Compose stack invoke."""

from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from rest_framework_api_key.models import APIKey

from apps.companies.models import Company
from apps.documents.models import Document

pytestmark = pytest.mark.django_db


def _run(command: str, *args: str) -> str:
    out = StringIO()
    call_command(command, *args, stdout=out)
    return out.getvalue()


# -- seed_user ---------------------------------------------------------------------------


def test_seed_user_creates_the_internal_manager() -> None:
    output = _run("seed_user", "--username", "manager", "--password", "secret")

    user = get_user_model().objects.get(username="manager")
    assert user.check_password("secret")
    assert user.is_staff
    assert "Created" in output


def test_seed_user_is_idempotent_and_resets_the_password() -> None:
    _run("seed_user", "--username", "manager", "--password", "first")
    output = _run("seed_user", "--username", "manager", "--password", "second")

    assert get_user_model().objects.filter(username="manager").count() == 1
    assert get_user_model().objects.get(username="manager").check_password("second")
    assert "Updated" in output


# -- API key commands --------------------------------------------------------------------


def test_create_api_key_prints_the_plaintext_once() -> None:
    output = _run("create_api_key", "n8n")

    api_key = APIKey.objects.get(name="n8n")
    assert api_key.prefix in output
    assert "not recoverable" in output


def test_revoke_api_key_blocks_the_key() -> None:
    _run("create_api_key", "n8n")
    prefix = APIKey.objects.get(name="n8n").prefix

    output = _run("revoke_api_key", prefix)

    assert APIKey.objects.get(prefix=prefix).revoked is True
    assert "Revoked" in output


def test_revoking_an_unknown_prefix_fails_loudly() -> None:
    with pytest.raises(CommandError):
        _run("revoke_api_key", "nosuch")


# -- seed_demo ---------------------------------------------------------------------------


def test_seed_demo_creates_a_company_and_a_document() -> None:
    output = _run("seed_demo")

    company = Company.objects.get()
    assert company.documents.count() == 1
    assert Document.objects.get().created_by == "seed_demo"
    assert "Created company" in output


def test_seed_demo_does_not_call_a_real_provider_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.core.management.commands import seed_demo

    def explode() -> object:
        raise AssertionError("seed_demo must not resolve the real gateway by default")

    monkeypatch.setattr(seed_demo, "get_zapsign_gateway", explode)

    _run("seed_demo")

    assert Document.objects.count() == 1


def test_seed_demo_is_idempotent() -> None:
    _run("seed_demo")
    output = _run("seed_demo")

    assert Company.objects.count() == 1
    assert Document.objects.count() == 1
    assert "nothing else to seed" in output
