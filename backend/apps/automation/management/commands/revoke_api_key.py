"""Revoke an automation API key by prefix; subsequent calls with it are rejected."""

from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from rest_framework_api_key.models import APIKey


class Command(BaseCommand):
    """``manage.py revoke_api_key <prefix>``."""

    help = "Revoke an API key by its prefix (FR-024)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("prefix", help="The key prefix shown at creation time.")

    def handle(self, *args: Any, **options: Any) -> None:
        prefix: str = options["prefix"]
        try:
            api_key = APIKey.objects.get(prefix=prefix)
        except APIKey.DoesNotExist as exc:
            raise CommandError(f"No API key with prefix {prefix!r}.") from exc

        api_key.revoked = True
        api_key.save()
        self.stdout.write(self.style.SUCCESS(f"Revoked API key {api_key.name!r} ({prefix})."))
