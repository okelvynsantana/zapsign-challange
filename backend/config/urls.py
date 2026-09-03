"""Root URL configuration.

Placeholder only: T021 wires the real routes (``/api/health/``, ``/api/auth/`` and the
per-app routers under ``/api/``). Keep this list empty until then so the project stays
importable without depending on views that other tasks own.
"""

from django.urls import URLPattern, URLResolver

urlpatterns: list[URLPattern | URLResolver] = []
