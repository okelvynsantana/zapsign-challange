"""Routes for the `signers` app."""

from django.urls import URLPattern, URLResolver, include, path
from rest_framework.routers import DefaultRouter

from apps.signers.views import SignerViewSet

app_name = "signers"

router = DefaultRouter()
router.register("signers", SignerViewSet, basename="signer")

urlpatterns: list[URLPattern | URLResolver] = [path("", include(router.urls))]
