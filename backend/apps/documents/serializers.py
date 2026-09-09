"""`Document` representation and validation (contracts/rest-api.md "Documents")."""

from typing import Any

from rest_framework import serializers

from apps.companies.models import Company
from apps.documents.models import Document, DocumentAnalysis
from apps.signers.models import Signer
from apps.signers.serializers import SignerSerializer, SignerWriteSerializer

__all__ = [
    "AlertSerializer",
    "DocumentAnalysisSerializer",
    "DocumentReportSerializer",
    "DocumentSerializer",
    "SummaryReportSerializer",
]

PROVIDER_OWNED_FIELDS = ("provider_status", "status", "open_id", "token", "last_provider_error")


class DocumentAnalysisSerializer(serializers.ModelSerializer):
    """One analysis run (contracts/rest-api.md `DocumentAnalysis` shape)."""

    error_reason = serializers.SerializerMethodField()

    class Meta:
        model = DocumentAnalysis
        fields = (
            "id",
            "state",
            "summary",
            "missing_topics",
            "insights",
            "source",
            "model",
            "error_reason",
            "created_at",
        )
        read_only_fields = fields

    def get_error_reason(self, instance: DocumentAnalysis) -> str | None:
        """`null` rather than `""` when the run succeeded, per the contract."""
        return instance.error_reason or None


class DocumentSerializer(serializers.ModelSerializer):
    """Read and write shape for a document and its signers.

    Provider-owned fields are read-only here: they are only ever written by the service
    from a ZapSign response or a resync, never from client input (data-model.md).
    """

    company = serializers.PrimaryKeyRelatedField[Company](queryset=Company.objects.all())
    signers = SignerWriteSerializer(many=True)
    latest_analysis = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = (
            "id",
            "company",
            "name",
            "pdf_url",
            "external_id",
            "provider_status",
            "status",
            "open_id",
            "token",
            "created_by",
            "last_provider_error",
            "signers",
            "latest_analysis",
            "created_at",
            "last_updated_at",
        )
        read_only_fields = (
            "id",
            "created_by",
            "created_at",
            "last_updated_at",
            *PROVIDER_OWNED_FIELDS,
        )
        extra_kwargs = {"name": {"allow_blank": False, "trim_whitespace": True}}

    def to_representation(self, instance: Document) -> dict[str, Any]:
        data = super().to_representation(instance)
        data["signers"] = SignerSerializer(instance.signers.all(), many=True).data
        return data

    def get_latest_analysis(self, instance: Document) -> dict[str, Any] | None:
        """The newest analysis, or `null` before the first run (FR-018)."""
        latest = instance.latest_analysis
        return DocumentAnalysisSerializer(latest).data if latest is not None else None

    def validate_signers(self, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not value:
            raise serializers.ValidationError("At least one signer is required.")

        emails = [str(signer["email"]).strip().lower() for signer in value]
        if len(set(emails)) != len(emails):
            raise serializers.ValidationError("The same email cannot appear twice on one document.")
        return value

    def get_fields(self) -> dict[str, serializers.Field]:
        fields = super().get_fields()
        if self.instance is not None:
            # Signers are optional on update: a PATCH of the name alone must not wipe them.
            fields["signers"].required = False
            fields["company"].required = False
        return fields

    def create(self, validated_data: dict[str, Any]) -> Document:
        raise NotImplementedError(
            "Documents are created through apps.documents.services.create_document, "
            "which persists locally before contacting the provider (FR-008)."
        )

    def update(self, instance: Document, validated_data: dict[str, Any]) -> Document:
        signers = validated_data.pop("signers", None)
        document = super().update(instance, validated_data)

        if signers is not None:
            # Replace the set wholesale: the payload is the full intended list (FR-006).
            document.signers.all().delete()
            Signer.objects.bulk_create(
                Signer(
                    document=document,
                    name=signer["name"],
                    email=str(signer["email"]).strip().lower(),
                    external_id=signer.get("external_id", ""),
                )
                for signer in signers
            )
        return document


class ReportSignerSerializer(serializers.ModelSerializer):
    """The signer fields a report exposes — no tokens, no internal ids."""

    class Meta:
        model = Signer
        fields = ("name", "email", "status")
        read_only_fields = fields


class DocumentReportSerializer(serializers.Serializer):
    """`GET /api/documents/{id}/report/` (contracts/rest-api.md, FR-025)."""

    document_id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    provider_status = serializers.CharField(read_only=True)
    signature_status = serializers.CharField(read_only=True, allow_null=True)
    signers = ReportSignerSerializer(many=True, read_only=True)
    latest_analysis = DocumentAnalysisSerializer(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)
    last_updated_at = serializers.DateTimeField(read_only=True)


class RiskInsightSerializer(serializers.Serializer):
    """One risk-flagged insight, with the document it came from."""

    document_id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    text = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class SummaryReportSerializer(serializers.Serializer):
    """`GET /api/reports/summary/` (contracts/rest-api.md, FR-026)."""

    total_documents = serializers.IntegerField(read_only=True)
    by_provider_status = serializers.DictField(child=serializers.IntegerField(), read_only=True)
    by_signature_status = serializers.DictField(child=serializers.IntegerField(), read_only=True)
    documents_with_risk_insight = serializers.IntegerField(read_only=True)
    recent_risk_insights = RiskInsightSerializer(many=True, read_only=True)
    generated_at = serializers.DateTimeField(read_only=True)


class AlertSerializer(serializers.Serializer):
    """One dashboard alert (bonus US5) — a derived view, never a stored row."""

    type = serializers.CharField(read_only=True)
    document_id = serializers.UUIDField(read_only=True)
    document_name = serializers.CharField(read_only=True)
    detail = serializers.CharField(read_only=True)
    since = serializers.DateTimeField(read_only=True)
