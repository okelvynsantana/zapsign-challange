"""The `Company` model — the organization documents are sent for signature on behalf of.

This model *is* the domain layer for its concern (plan.md "Architecture stance"): the
credential-masking rule and the non-empty-name invariant live here as behaviour, so they
hold for the API, the admin, a management command or a shell session alike.
"""

from typing import Any

from django.core.exceptions import ValidationError
from django.db import models

from apps.companies.querysets import CompanyQuerySet
from apps.core.models import TimeStampedModel, UUIDModel
from apps.core.values import SecretString

__all__ = ["Company"]


class CompanyManager(models.Manager.from_queryset(CompanyQuerySet)):  # type: ignore[misc]
    """Concrete manager so the custom queryset is statically resolvable."""


class Company(UUIDModel, TimeStampedModel):
    """An organization and the ZapSign credential used on its behalf (FR-001, FR-003)."""

    name = models.CharField(max_length=255)
    api_token = models.CharField(
        max_length=255,
        help_text=(
            "ZapSign account API token. Write-only across the API: it is never serialized "
            "back in full and never reaches an automation endpoint (FR-002)."
        ),
    )

    objects = CompanyManager()

    class Meta:
        verbose_name_plural = "companies"
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name

    # -- domain behaviour --------------------------------------------------------------

    @property
    def secret_token(self) -> SecretString:
        """The credential wrapped so it cannot leak through an f-string or a traceback."""
        return SecretString(self.api_token)

    @property
    def masked_token(self) -> str:
        """The credential with everything but its last four characters hidden (FR-002)."""
        return self.secret_token.masked()

    def clean(self) -> None:
        super().clean()
        if not self.name.strip():
            raise ValidationError({"name": "The organization name cannot be blank."})

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.name = self.name.strip()
        super().save(*args, **kwargs)
