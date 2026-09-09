"""Seed a demo organization and document so the quickstart has something to look at."""

from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from apps.companies.models import Company
from apps.documents.services import DocumentDraft, SignerDraft, create_document
from apps.integrations.providers import get_analysis_pipeline, get_zapsign_gateway
from apps.integrations.zapsign.fakes import FakeZapSignGateway
from apps.integrations.zapsign.gateway import ZapSignGateway


class Command(BaseCommand):
    """``manage.py seed_demo`` — idempotent, safe to re-run."""

    help = "Create a demo Company and one Document (with signer and analysis)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--company", default="Acme Ltda")
        parser.add_argument("--api-token", default="demo-zapsign-token")
        parser.add_argument(
            "--pdf-url",
            default="https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
        )
        parser.add_argument(
            "--real-provider",
            action="store_true",
            help=(
                "Submit the demo document to the configured ZapSign environment. Off by "
                "default: the seeded token is a placeholder, so a real call would only "
                "produce a 403 and a failed document."
            ),
        )

    def handle(self, *args: Any, **options: Any) -> None:
        company, created = Company.objects.get_or_create(
            name=options["company"],
            defaults={"api_token": options["api_token"]},
        )
        verb = "Created" if created else "Reusing"
        self.stdout.write(self.style.SUCCESS(f"{verb} company {company.name!r}."))

        if company.documents.exists():
            self.stdout.write("Company already has documents; nothing else to seed.")
            return

        document = create_document(
            DocumentDraft(
                company=company,
                name="Contrato de Prestação de Serviços (demo)",
                pdf_url=options["pdf_url"],
                signers=(SignerDraft(name="Ana Souza", email="ana@example.com"),),
                created_by="seed_demo",
            ),
            gateway=self._gateway(real_provider=options["real_provider"]),
            pipeline=get_analysis_pipeline(),
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Created document {document.name!r} (provider_status={document.provider_status})."
            )
        )

    @staticmethod
    def _gateway(*, real_provider: bool) -> ZapSignGateway:
        """The demo seeder must not call a real provider with a placeholder token."""
        return get_zapsign_gateway() if real_provider else FakeZapSignGateway()
