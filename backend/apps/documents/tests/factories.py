"""T057 — `Document` factory (shared with the companies delete-guard test)."""

import factory

from apps.companies.tests.factories import CompanyFactory
from apps.documents.models import Document
from apps.documents.status import ProviderStatus


class DocumentFactory(factory.django.DjangoModelFactory[Document]):
    """A document already submitted to ZapSign unless the test says otherwise."""

    class Meta:
        model = Document

    company = factory.SubFactory(CompanyFactory)
    name = factory.Sequence(lambda n: f"Contrato {n}")
    pdf_url = factory.Sequence(lambda n: f"https://files.example.test/contrato-{n}.pdf")
    provider_status = ProviderStatus.SUBMITTED
    open_id = factory.Sequence(lambda n: 100000 + n)
    token = factory.Sequence(lambda n: f"zapsign-doc-token-{n}")
    status = "pending"
    created_by = "manager"
