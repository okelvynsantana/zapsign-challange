"""Create the internal manager account the SPA logs in with (idempotent)."""

from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandParser

from config.settings.env import env_str


class Command(BaseCommand):
    """``manage.py seed_user`` — used by the Compose `migrate` service and the k8s job."""

    help = "Create or update the internal manager user from SEED_USERNAME/SEED_PASSWORD."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--username", default=env_str("SEED_USERNAME", "manager"))
        parser.add_argument("--password", default=env_str("SEED_PASSWORD", "manager"))
        parser.add_argument("--email", default=env_str("SEED_EMAIL", ""))

    def handle(self, *args: Any, **options: Any) -> None:
        user_model = get_user_model()
        username: str = options["username"]
        password: str = options["password"]

        user, created = user_model.objects.get_or_create(
            username=username,
            defaults={"email": options["email"], "is_staff": True, "is_superuser": True},
        )
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.save()

        verb = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{verb} internal user {username!r}."))
