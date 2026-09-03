"""Django application configuration for the `documents` app."""

from django.apps import AppConfig


class DocumentsConfig(AppConfig):
    """App config for `apps.documents`."""

    name: str = "apps.documents"
    label: str = "documents"
    default_auto_field: str = "django.db.models.BigAutoField"
