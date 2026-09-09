"""Issue an automation API key. The plaintext key is printed once and never again."""

from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from rest_framework_api_key.models import APIKey


class Command(BaseCommand):
    """``manage.py create_api_key "n8n"``."""

    help = "Create an API key for an automation consumer and print it once."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("name", help="Which integration this key is for.")

    def handle(self, *args: Any, **options: Any) -> None:
        api_key, key = APIKey.objects.create_key(name=options["name"])
        self.stdout.write(self.style.SUCCESS(f"API key created for {api_key.name!r}."))
        self.stdout.write(f"prefix: {api_key.prefix}")
        self.stdout.write(f"key:    {key}")
        self.stdout.write(self.style.WARNING("Store it now — this value is not recoverable."))
