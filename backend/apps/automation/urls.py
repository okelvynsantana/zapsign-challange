"""Automation namespace routes — API-key only (contracts/rest-api.md)."""

from django.urls import URLPattern, URLResolver, path

from apps.automation.views import (
    AutomationAnalyzeView,
    AutomationDocumentCreateView,
    AutomationDocumentReportView,
    AutomationSummaryReportView,
)

app_name = "automation"

urlpatterns: list[URLPattern | URLResolver] = [
    path("documents/", AutomationDocumentCreateView.as_view(), name="document-create"),
    path(
        "documents/<uuid:pk>/analyze/",
        AutomationAnalyzeView.as_view(),
        name="document-analyze",
    ),
    path(
        "documents/<uuid:pk>/report/",
        AutomationDocumentReportView.as_view(),
        name="document-report",
    ),
    path("reports/summary/", AutomationSummaryReportView.as_view(), name="report-summary"),
]
