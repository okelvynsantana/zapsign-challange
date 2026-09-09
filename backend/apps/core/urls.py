"""Core routes: the unauthenticated health endpoint."""

from django.urls import path

from apps.core.health import HealthView

app_name = "core"

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
]
