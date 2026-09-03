"""The `Document` model — the system of record for a file sent for signature.

Business rules live here as model behaviour (plan.md "Architecture stance"): whether a
resync is allowed, and how a provider result or failure is folded into the row. The
service layer orchestrates the external call; the decisions are the model's.
"""

from typing import TYPE_CHECKING, Any

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import models

from apps.core.models import TimeStampedModel, UUIDModel
from apps.documents.querysets import DocumentQuerySet
from apps.documents.status import ProviderStatus, can_resync

if TYPE_CHECKING:
    from apps.integrations.zapsign.gateway import (
        ZapSignCreateResult,
        ZapSignDocumentStatus,
    )

__all__ = ["Document", "DocumentAnalysis"]

MAX_PROVIDER_ERROR_CHARS = 500


class DocumentManager(models.Manager.from_queryset(DocumentQuerySet)):  # type: ignore[misc]
    """Concrete manager so the custom queryset is statically resolvable."""


class Document(UUIDModel, TimeStampedModel):
    """A file to be signed, persisted locally before any external call (FR-008)."""

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.PROTECT,
        related_name="documents",
        help_text="Deleting a company with documents is refused rather than orphaning them.",
    )
    name = models.CharField(max_length=255)
    pdf_url = models.URLField(
        max_length=2048,
        validators=[URLValidator(schemes=["http", "https"])],
    )

    provider_status = models.CharField(
        max_length=32,
        choices=ProviderStatus.choices,
        default=ProviderStatus.PENDING_INTEGRATION,
        db_index=True,
        help_text="Our ZapSign hand-off lifecycle; drives the retry path (FR-010).",
    )
    open_id = models.IntegerField(null=True, blank=True)
    token = models.CharField(max_length=255, blank=True, default="")
    external_id = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True,
        help_text="Signature status as reported by ZapSign; never computed locally (FR-013).",
    )
    created_by = models.CharField(max_length=255, blank=True, default="")
    last_provider_error = models.TextField(blank=True, default="")

    objects = DocumentManager()

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["company", "-created_at"])]

    def __str__(self) -> str:
        return self.name

    # -- domain behaviour --------------------------------------------------------------

    def can_resync(self) -> bool:
        """Whether a resync may be triggered right now (FR-010)."""
        return can_resync(self.provider_status)

    def mark_submitted(self, result: "ZapSignCreateResult | ZapSignDocumentStatus") -> None:
        """Fold a successful provider response into this row (does not save)."""
        self.open_id = result.open_id
        self.token = result.token
        self.status = result.status
        self.provider_status = ProviderStatus.SUBMITTED
        self.last_provider_error = ""
        external_id = getattr(result, "external_id", None)
        if external_id:
            self.external_id = external_id

    def mark_provider_failed(self, reason: str) -> None:
        """Record a retryable provider failure with its reason (does not save)."""
        self.provider_status = ProviderStatus.FAILED
        self.last_provider_error = reason[:MAX_PROVIDER_ERROR_CHARS]

    @property
    def latest_analysis(self) -> "DocumentAnalysis | None":
        """The current analysis: the newest row (FR-018). `None` before the first run."""
        return self.analyses.order_by("-created_at").first()

    @property
    def has_open_risk(self) -> bool:
        """Whether the *latest* analysis succeeded and flagged a risk (FR-030, FR-031)."""
        latest = self.latest_analysis
        return latest is not None and latest.has_risk_insight

    def clean(self) -> None:
        super().clean()
        if not self.name.strip():
            raise ValidationError({"name": "The document name cannot be blank."})

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.name = self.name.strip()
        super().save(*args, **kwargs)


class DocumentAnalysis(UUIDModel):
    """One analysis run, insert-only.

    A retry is a *new row*, never an update: the history is the audit trail the
    constitution requires (Principle VI, FR-017). Nothing in the codebase offers an update
    path for these — not the service, not the serializer.
    """

    class State(models.TextChoices):
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    class Source(models.TextChoices):
        LLM = "llm", "Model"
        REGEX = "regex", "Rule-based"
        LLM_REGEX = "llm+regex", "Model + rules"

    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="analyses",
    )
    state = models.CharField(max_length=16, choices=State.choices)
    summary = models.TextField(blank=True, default="")
    missing_topics = models.JSONField(default=list, blank=True)
    insights = models.JSONField(
        default=list,
        blank=True,
        help_text='Each entry is {"text": str, "risk": bool}.',
    )
    source = models.CharField(max_length=16, choices=Source.choices)
    error_reason = models.CharField(max_length=255, blank=True, default="")
    model = models.CharField(max_length=128, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name_plural = "document analyses"
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["document", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.state} analysis of {self.document_id}"

    # -- domain behaviour --------------------------------------------------------------

    @property
    def has_risk_insight(self) -> bool:
        """True when this run succeeded and any insight is risk-flagged."""
        if self.state != self.State.SUCCEEDED:
            return False
        return any(bool(item.get("risk")) for item in self.insights if isinstance(item, dict))

    @property
    def risk_insights(self) -> list[dict[str, Any]]:
        """Just the risk-flagged insights, for the alerts dashboard and the webhook."""
        return [item for item in self.insights if isinstance(item, dict) and bool(item.get("risk"))]

    def clean(self) -> None:
        super().clean()
        if self.state == self.State.SUCCEEDED and self.error_reason:
            raise ValidationError({"error_reason": "A succeeded analysis carries no reason."})
        if self.state == self.State.FAILED and not self.error_reason:
            raise ValidationError({"error_reason": "A failed analysis must record a reason."})
