"""T029 — `Company` model rules (US1: FR-001, FR-002).

The model is the domain layer here (plan.md "Architecture stance"): masking and the
non-empty-name invariant are model behaviour, not serializer behaviour, so they hold no
matter which surface writes the row.
"""

import uuid

import pytest
from django.core.exceptions import ValidationError

from apps.companies.models import Company

pytestmark = pytest.mark.django_db


def test_primary_key_is_a_generated_uuid() -> None:
    company = Company.objects.create(name="Acme Ltda", api_token="zapsign-token-abcd")

    assert isinstance(company.pk, uuid.UUID)
    assert company.pk.version == 4


def test_masked_token_hides_everything_but_the_last_four_characters() -> None:
    company = Company(name="Acme", api_token="super-secret-value-3f9a")

    masked = company.masked_token

    assert masked.endswith("3f9a")
    assert "super-secret" not in masked
    assert len(masked) == len("super-secret-value-3f9a")


def test_masked_token_of_a_short_credential_reveals_nothing() -> None:
    assert set(Company(name="Acme", api_token="abcd").masked_token) == {"•"}


def test_masked_token_of_a_blank_credential_is_empty() -> None:
    assert Company(name="Acme", api_token="").masked_token == ""


def test_clean_rejects_a_blank_name() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Company(name="   ", api_token="token-value").full_clean()

    assert "name" in exc_info.value.message_dict


def test_name_is_trimmed_on_save() -> None:
    company = Company.objects.create(name="  Acme Ltda  ", api_token="token-value")
    company.refresh_from_db()

    assert company.name == "Acme Ltda"


def test_secret_token_never_renders_in_full_through_str_or_repr() -> None:
    company = Company(name="Acme", api_token="super-secret-value-3f9a")

    assert "super-secret-value-3f9a" not in str(company.secret_token)
    assert "super-secret-value-3f9a" not in repr(company.secret_token)
    assert company.secret_token.reveal() == "super-secret-value-3f9a"
