"""T036 — factories for `Company`, reused by every downstream app's tests."""

import factory

from apps.companies.models import Company


class CompanyFactory(factory.django.DjangoModelFactory[Company]):
    """A company with a plausible ZapSign sandbox credential."""

    class Meta:
        model = Company

    name = factory.Sequence(lambda n: f"Acme Ltda {n}")
    api_token = factory.Sequence(lambda n: f"zapsign-sandbox-token-{n:04d}")
