"""Django application configuration for the `integrations` app."""

from django.apps import AppConfig


class IntegrationsConfig(AppConfig):
    """App config for `apps.integrations`."""

    name: str = "apps.integrations"
    label: str = "integrations"
    default_auto_field: str = "django.db.models.BigAutoField"
