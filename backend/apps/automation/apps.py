"""Django application configuration for the `automation` app."""

from django.apps import AppConfig


class AutomationConfig(AppConfig):
    """App config for `apps.automation`."""

    name: str = "apps.automation"
    label: str = "automation"
    default_auto_field: str = "django.db.models.BigAutoField"
