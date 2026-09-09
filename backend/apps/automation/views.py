"""The `/api/automation/**` surface — the stable, API-key-only entry point for n8n.

Deliberately thin: it reuses exactly the same services and reports as the SPA endpoints
(FR-022), so the two surfaces can never drift apart. What differs is only the credential
it accepts and the fact that nothing here can expose a ZapSign token (FR-002).
"""

from typing import Any

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.automation.auth import ApiKeyAuthentication, HasApiKey, api_key_name
from apps.documents.models import Document
from apps.documents.reports import document_report, summary_report
from apps.documents.serializers import (
    DocumentAnalysisSerializer,
    DocumentReportSerializer,
    DocumentSerializer,
    SummaryReportSerializer,
)
from apps.documents.services import (
    DocumentDraft,
    SignerDraft,
    analyze_document,
    create_document,
)
from apps.integrations.providers import (
    get_analysis_pipeline,
    get_webhook_notifier,
    get_zapsign_gateway,
)

__all__ = [
    "AutomationAnalyzeView",
    "AutomationDocumentCreateView",
    "AutomationDocumentReportView",
    "AutomationSummaryReportView",
]


class AutomationView(APIView):
    """Base class fixing the credential rule for the whole namespace.

    Only `Authorization: Api-Key <key>` is accepted here; a JWT is rejected, so an
    integration key can never stand in for a full SPA session and vice versa.
    """

    authentication_classes = [ApiKeyAuthentication]
    permission_classes = [HasApiKey]

    def _document(self, pk: str) -> Document:
        return get_object_or_404(Document.objects.all().with_signers(), pk=pk)


class AutomationDocumentCreateView(AutomationView):
    """`POST /api/automation/documents/` — same behaviour as the SPA create (FR-022)."""

    @extend_schema(request=DocumentSerializer, responses={201: DocumentSerializer})
    def post(self, request: Request) -> Response:
        serializer = DocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data: dict[str, Any] = serializer.validated_data

        document = create_document(
            DocumentDraft(
                company=data["company"],
                name=data["name"],
                pdf_url=data["pdf_url"],
                signers=tuple(
                    SignerDraft(name=signer["name"], email=signer["email"])
                    for signer in data["signers"]
                ),
                external_id=data.get("external_id") or None,
                created_by=api_key_name(request),
            ),
            gateway=get_zapsign_gateway(),
            pipeline=get_analysis_pipeline(),
            notifier=get_webhook_notifier(),
        )
        return Response(DocumentSerializer(document).data, status=status.HTTP_201_CREATED)


class AutomationAnalyzeView(AutomationView):
    """`POST /api/automation/documents/{id}/analyze/` — a fresh analysis run (FR-016)."""

    @extend_schema(request=None, responses={201: DocumentAnalysisSerializer})
    def post(self, request: Request, pk: str) -> Response:
        analysis = analyze_document(
            self._document(pk),
            pipeline=get_analysis_pipeline(),
            notifier=get_webhook_notifier(),
        )
        return Response(
            DocumentAnalysisSerializer(analysis).data,
            status=status.HTTP_201_CREATED,
        )


class AutomationDocumentReportView(AutomationView):
    """`GET /api/automation/documents/{id}/report/` (FR-025)."""

    @extend_schema(responses={200: DocumentReportSerializer})
    def get(self, request: Request, pk: str) -> Response:
        return Response(DocumentReportSerializer(document_report(self._document(pk))).data)


class AutomationSummaryReportView(AutomationView):
    """`GET /api/automation/reports/summary/` (FR-026)."""

    @extend_schema(responses={200: SummaryReportSerializer})
    def get(self, request: Request) -> Response:
        return Response(SummaryReportSerializer(summary_report()).data)
