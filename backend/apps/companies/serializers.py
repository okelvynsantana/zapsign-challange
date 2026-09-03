"""`Company` representation and validation (contracts/rest-api.md "Companies")."""

from typing import Any

from rest_framework import serializers

from apps.companies.models import Company

__all__ = ["CompanySerializer"]


class CompanySerializer(serializers.ModelSerializer):
    """Read side exposes only the masked credential; the raw one is write-only (FR-002).

    On update the credential is optional: omitting it — or sending `""` — keeps the stored
    value, so renaming the organization can never wipe its token (data-model.md).
    """

    api_token = serializers.CharField(
        write_only=True,
        required=True,
        allow_blank=False,
        max_length=255,
        trim_whitespace=True,
    )
    api_token_masked = serializers.CharField(source="masked_token", read_only=True)

    class Meta:
        model = Company
        fields = (
            "id",
            "name",
            "api_token",
            "api_token_masked",
            "created_at",
            "last_updated_at",
        )
        read_only_fields = ("id", "created_at", "last_updated_at")
        extra_kwargs = {"name": {"allow_blank": False, "trim_whitespace": True}}

    def get_fields(self) -> dict[str, serializers.Field]:
        fields = super().get_fields()
        if self.instance is not None:
            # Update: the credential may be omitted entirely or sent blank.
            api_token = fields["api_token"]
            assert isinstance(api_token, serializers.CharField)
            api_token.required = False
            api_token.allow_blank = True
        return fields

    def update(self, instance: Company, validated_data: dict[str, Any]) -> Company:
        if not validated_data.get("api_token"):
            validated_data.pop("api_token", None)
        return super().update(instance, validated_data)
