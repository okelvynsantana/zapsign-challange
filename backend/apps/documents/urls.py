"""Routes for the `documents` app."""

from django.urls import URLPattern, URLResolver, include, path
from rest_framework.routers import DefaultRouter

from apps.documents.views import AlertListView, DocumentViewSet, ReportSummaryView

app_name = "documents"

router = DefaultRouter()
router.register("documents", DocumentViewSet, basename="document")

urlpatterns: list[URLPattern | URLResolver] = [
    path("reports/summary/", ReportSummaryView.as_view(), name="report-summary"),
    path("alerts/", AlertListView.as_view(), name="alert-list"),
    path("", include(router.urls)),
]
