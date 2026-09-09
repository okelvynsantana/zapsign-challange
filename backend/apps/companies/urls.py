"""Routes for the `companies` app."""

from django.urls import URLPattern, URLResolver, include, path
from rest_framework.routers import DefaultRouter

from apps.companies.views import CompanyViewSet

app_name = "companies"

router = DefaultRouter()
router.register("companies", CompanyViewSet, basename="company")

urlpatterns: list[URLPattern | URLResolver] = [path("", include(router.urls))]
