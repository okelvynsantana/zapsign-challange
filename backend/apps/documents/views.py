"""`Document` HTTP surface.

The viewset stays thin: it validates through the serializer, hands the multi-model +
external-call work to `apps.documents.services`, and renders the result.
"""

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.automation.auth import ApiKeyAuthentication, IsAuthenticatedOrHasApiKey
from apps.documents.alerts import build_alerts
from apps.documents.models import Document
from apps.documents.reports import document_report, summary_report
from apps.documents.serializers import (
    AlertSerializer,
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
    resync_document,
)
from apps.integrations.providers import (
    get_analysis_pipeline,
    get_webhook_notifier,
    get_zapsign_gateway,
)

__all__ = ["AlertListView", "DocumentViewSet", "ReportSummaryView"]


class DocumentViewSet(viewsets.ModelViewSet):
    """CRUD plus the provider actions (FR-005 … FR-013)."""

    serializer_class = DocumentSerializer
    queryset = Document.objects.all()

    def get_queryset(self) -> QuerySet[Document]:
        queryset = (
            Document.objects.all().with_signers().with_latest_analysis().select_related("company")
        )
        params = self.request.query_params

        if provider_status := params.get("provider_status"):
            queryset = queryset.by_provider_status(provider_status)
        if signature_status := params.get("status"):
            queryset = queryset.by_signature_status(signature_status)
        if company := params.get("company"):
            queryset = queryset.for_company(company)
        return queryset

    def create(self, request: Request, *args: object, **kwargs: object) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

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
                created_by=self._actor(request),
            ),
            gateway=get_zapsign_gateway(),
            pipeline=get_analysis_pipeline(),
            notifier=get_webhook_notifier(),
        )

        # 201 stands even when the provider call failed: the local resource was created.
        return Response(
            self.get_serializer(document).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=None, responses={200: DocumentSerializer})
    @action(detail=True, methods=["post"])
    def resync(self, request: Request, pk: str | None = None) -> Response:
        """Re-submit a failed document, or refresh a submitted one (FR-010)."""
        document = resync_document(
            self.get_object(),
            gateway=get_zapsign_gateway(),
            notifier=get_webhook_notifier(),
        )
        return Response(self.get_serializer(document).data)

    @extend_schema(request=None, responses={201: DocumentAnalysisSerializer})
    @action(detail=True, methods=["post"])
    def analyze(self, request: Request, pk: str | None = None) -> Response:
        """Run a fresh analysis, appended to the document's history (FR-016, FR-017)."""
        analysis = analyze_document(
            self.get_object(),
            pipeline=get_analysis_pipeline(),
            notifier=get_webhook_notifier(),
        )
        return Response(
            DocumentAnalysisSerializer(analysis).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(responses={200: DocumentAnalysisSerializer(many=True)})
    @action(detail=True, methods=["get"])
    def analyses(self, request: Request, pk: str | None = None) -> Response:
        """The full analysis history, newest first (FR-018)."""
        history = self.get_object().analyses.order_by("-created_at")
        page = self.paginate_queryset(history)
        serializer = DocumentAnalysisSerializer(page if page is not None else history, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @extend_schema(responses={200: DocumentReportSerializer})
    @action(
        detail=True,
        methods=["get"],
        authentication_classes=[JWTAuthentication, ApiKeyAuthentication],
        permission_classes=[IsAuthenticatedOrHasApiKey],
    )
    def report(self, request: Request, pk: str | None = None) -> Response:
        """Per-document report — consumed by the SPA and by automation alike (FR-025)."""
        return Response(DocumentReportSerializer(document_report(self.get_object())).data)

    @staticmethod
    def _actor(request: Request) -> str:
        user = getattr(request, "user", None)
        return user.get_username() if user is not None and user.is_authenticated else ""


class ReportSummaryView(APIView):
    """`GET /api/reports/summary/` — the aggregated report (FR-026).

    Reachable with either credential: the SPA renders it, and automation pulls it.
    """

    authentication_classes = [JWTAuthentication, ApiKeyAuthentication]
    permission_classes = [IsAuthenticatedOrHasApiKey]

    @extend_schema(responses={200: SummaryReportSerializer})
    def get(self, request: Request) -> Response:
        return Response(SummaryReportSerializer(summary_report()).data)


class AlertListView(APIView):
    """`GET /api/alerts/` — documents needing attention (bonus US5, FR-030).

    Nothing matching is an empty list with `200`, not an error (US5 AS-3).
    """

    @extend_schema(responses={200: AlertSerializer(many=True)})
    def get(self, request: Request) -> Response:
        return Response(AlertSerializer(build_alerts(), many=True).data)
