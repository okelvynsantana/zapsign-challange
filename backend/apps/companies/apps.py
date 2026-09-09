"""Django application configuration for the `companies` app."""

from django.apps import AppConfig


class CompaniesConfig(AppConfig):
    """App config for `apps.companies`."""

    name: str = "apps.companies"
    label: str = "companies"
    default_auto_field: str = "django.db.models.BigAutoField"
