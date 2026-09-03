"""Document provider-status vocabulary and transition rules.

Pure: no model import, so the rules can be reasoned about and tested on their own. The
model stores the string and delegates the decisions here.
"""

from django.db.models import TextChoices

__all__ = ["RESYNCABLE_STATUSES", "ProviderStatus", "can_resync"]


class ProviderStatus(TextChoices):
    """*Our* lifecycle for the ZapSign hand-off — distinct from the signature status.

    ```
    pending_integration ──(create OK)──▶ submitted
    pending_integration ──(error/timeout)──▶ failed
    failed ──(resync)──▶ submitted | failed
    submitted ──(resync)──▶ submitted     (status refreshed from the provider)
    ```
    """

    PENDING_INTEGRATION = "pending_integration", "Pending integration"
    SUBMITTED = "submitted", "Submitted"
    FAILED = "failed", "Failed"


#: `pending_integration` means an attempt is in flight; re-triggering it would double-submit.
RESYNCABLE_STATUSES: frozenset[str] = frozenset({ProviderStatus.SUBMITTED, ProviderStatus.FAILED})


def can_resync(provider_status: str) -> bool:
    """Whether `POST /api/documents/{id}/resync/` is allowed from this state (FR-010)."""
    return provider_status in RESYNCABLE_STATUSES
