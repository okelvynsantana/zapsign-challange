"""Root URL configuration.

``/api/health/`` is unauthenticated (infra probes must not carry app credentials);
``/api/auth/`` issues and refreshes the SPA's JWT; every other route sits under ``/api/``
behind an authentication class.
"""

from django.contrib import admin
from django.urls import URLPattern, URLResolver, include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenRefreshView

from apps.core.auth import ContractTokenObtainPairView

urlpatterns: list[URLPattern | URLResolver] = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.core.urls")),
    path("api/auth/token/", ContractTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/", include("apps.companies.urls")),
    path("api/", include("apps.documents.urls")),
    path("api/", include("apps.signers.urls")),
    path("api/automation/", include("apps.automation.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
