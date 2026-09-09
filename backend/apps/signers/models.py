"""The `Signer` model — a person expected to sign one document."""

from typing import Any

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import models

from apps.core.models import UUIDModel
from apps.signers.querysets import SignerQuerySet

__all__ = ["Signer"]


class SignerManager(models.Manager.from_queryset(SignerQuerySet)):  # type: ignore[misc]
    """Concrete manager so the custom queryset is statically resolvable."""


class Signer(UUIDModel):
    """Belongs to exactly one document; deleting that document deletes it (FR-011)."""

    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="signers",
    )
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=320)
    token = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=64, blank=True, default="")
    external_id = models.CharField(max_length=255, blank=True, default="")

    objects = SignerManager()

    class Meta:
        ordering = ("email",)
        constraints = [
            # The same person may sign different documents, but not the same one twice.
            models.UniqueConstraint(
                fields=["document", "email"],
                name="unique_signer_email_per_document",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>"

    # -- domain behaviour --------------------------------------------------------------

    @property
    def normalized_email(self) -> str:
        """Lower-cased, trimmed email — what the uniqueness rule compares."""
        return self.email.strip().lower()

    def clean(self) -> None:
        super().clean()
        if not self.name.strip():
            raise ValidationError({"name": "The signer name cannot be blank."})
        validate_email(self.email)

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.name = self.name.strip()
        self.email = self.normalized_email
        super().save(*args, **kwargs)
