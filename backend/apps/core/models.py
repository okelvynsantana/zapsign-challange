"""Abstract model bases shared by every domain app.

Constitution Principle VI: every domain entity has a UUID v4 primary key, never a
sequential integer. Concrete models inherit these instead of restating the fields.
"""

from uuid import uuid4

from django.db import models

__all__ = ["TimeStampedModel", "UUIDModel"]


class UUIDModel(models.Model):
    """Base model with a server-generated, non-editable UUID v4 primary key."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    """Base model carrying insert and update timestamps (timezone-aware UTC)."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    last_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
