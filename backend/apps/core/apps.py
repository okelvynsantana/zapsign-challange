"""Django application configuration for the `core` app."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """App config for `apps.core`."""

    name: str = "apps.core"
    label: str = "core"
    default_auto_field: str = "django.db.models.BigAutoField"
