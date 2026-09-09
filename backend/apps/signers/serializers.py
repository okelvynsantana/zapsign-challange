"""`Signer` representation and validation (contracts/rest-api.md "Signers")."""

from typing import Any

from rest_framework import serializers

from apps.signers.models import Signer

__all__ = ["SignerSerializer", "SignerWriteSerializer"]


class SignerSerializer(serializers.ModelSerializer):
    """Full signer resource. `token`/`status` are written only from provider data."""

    class Meta:
        model = Signer
        fields = ("id", "document", "name", "email", "token", "status", "external_id")
        read_only_fields = ("id", "token", "status")

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        document = attrs.get("document") or getattr(self.instance, "document", None)
        email: str = attrs.get("email") or getattr(self.instance, "email", "") or ""
        normalized = email.strip().lower()

        duplicates = Signer.objects.for_document(getattr(document, "pk", None)).filter(
            email=normalized
        )
        if self.instance is not None:
            duplicates = duplicates.exclude(pk=self.instance.pk)

        if duplicates.exists():
            raise serializers.ValidationError(
                {"email": "This email is already a signer on this document."}
            )
        return attrs


class SignerWriteSerializer(serializers.ModelSerializer):
    """Nested form used inside a document payload — the document is implied."""

    class Meta:
        model = Signer
        fields = ("name", "email", "external_id")
