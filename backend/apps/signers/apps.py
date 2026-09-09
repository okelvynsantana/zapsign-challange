"""Django application configuration for the `signers` app."""

from django.apps import AppConfig


class SignersConfig(AppConfig):
    """App config for `apps.signers`."""

    name: str = "apps.signers"
    label: str = "signers"
    default_auto_field: str = "django.db.models.BigAutoField"
