"""Response serializers that exist purely to describe hand-written views in the schema."""

from rest_framework import serializers

__all__ = ["HealthSerializer"]


class HealthSerializer(serializers.Serializer):
    """The `/api/health/` body (FR-027)."""

    status = serializers.CharField(read_only=True)
    checks = serializers.DictField(child=serializers.CharField(), read_only=True)
