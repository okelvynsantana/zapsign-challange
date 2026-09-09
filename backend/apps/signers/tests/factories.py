"""T057 — `Signer` factory."""

import factory

from apps.documents.tests.factories import DocumentFactory
from apps.signers.models import Signer


class SignerFactory(factory.django.DjangoModelFactory[Signer]):
    """A signer attached to its own document unless one is passed in."""

    class Meta:
        model = Signer

    document = factory.SubFactory(DocumentFactory)
    name = factory.Sequence(lambda n: f"Signer {n}")
    email = factory.Sequence(lambda n: f"signer{n}@example.com")
