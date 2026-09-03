"""The single place a view or a service resolves an external provider from.

Callers ask for an interface and get whichever implementation the environment selects —
real by default, fake when `*_USE_FAKE` is on (offline local runs and the demo stack).
Nothing else in the codebase constructs a gateway, so swapping one is a one-line change
here (Constitution Principle I).
"""

from typing import TYPE_CHECKING

from apps.integrations.config import (
    DEFAULT_EXPECTED_CLAUSES,
    AnalysisConfig,
    PdfConfig,
    WebhookConfig,
    ZapSignConfig,
    get_integrations_config,
)
from apps.integrations.zapsign.gateway import ZapSignGateway

if TYPE_CHECKING:
    from apps.automation.webhook import WebhookNotifier
    from apps.integrations.analysis.pipeline import AnalysisPipeline

__all__ = ["get_analysis_pipeline", "get_webhook_notifier", "get_zapsign_gateway"]


def _zapsign_config() -> ZapSignConfig:
    return get_integrations_config().zapsign


def _analysis_config() -> AnalysisConfig:
    return get_integrations_config().analysis


def _pdf_config() -> PdfConfig:
    return get_integrations_config().pdf


def _webhook_config() -> WebhookConfig:
    return get_integrations_config().webhook


def get_zapsign_gateway() -> ZapSignGateway:
    """Return the configured ZapSign gateway (`ZAPSIGN_USE_FAKE` selects the fake)."""
    config = _zapsign_config()
    if config.use_fake:
        from apps.integrations.zapsign.fakes import FakeZapSignGateway

        return FakeZapSignGateway()

    from apps.integrations.zapsign.client import HttpZapSignGateway

    return HttpZapSignGateway(config)


def get_analysis_pipeline() -> "AnalysisPipeline":
    """Return the configured analysis pipeline (`AI_USE_FAKE` selects the fake provider)."""
    from apps.integrations.analysis.clause_checker import ClauseChecker
    from apps.integrations.analysis.pipeline import AnalysisPipeline

    analysis_config = _analysis_config()

    if analysis_config.use_fake or not analysis_config.api_key:
        # No key configured is the same situation as "explicitly faked": we must not try
        # to call OpenAI, and the document flow must keep working regardless.
        from apps.integrations.analysis.fakes import FakeAnalysisProvider
        from apps.integrations.pdf.fakes import FakePdfTextExtractor

        provider: object = FakeAnalysisProvider()
        extractor: object = FakePdfTextExtractor()
    else:
        from apps.integrations.analysis.openai_provider import OpenAIAnalysisProvider
        from apps.integrations.pdf.extractor import PypdfTextExtractor

        provider = OpenAIAnalysisProvider(analysis_config)
        extractor = PypdfTextExtractor(_pdf_config())

    return AnalysisPipeline(
        extractor=extractor,  # type: ignore[arg-type]
        provider=provider,  # type: ignore[arg-type]
        clause_checker=ClauseChecker(
            {label: [label] for label in analysis_config.expected_clauses}
            if analysis_config.expected_clauses != DEFAULT_EXPECTED_CLAUSES
            else None
        ),
        regex_fallback_enabled=analysis_config.regex_fallback_enabled,
    )


def get_webhook_notifier() -> "WebhookNotifier":
    """Return the outbound notifier; a blank `N8N_WEBHOOK_URL` turns the feature off."""
    from apps.automation.webhook import HttpWebhookNotifier, NullWebhookNotifier

    config = _webhook_config()
    return HttpWebhookNotifier(config) if config.enabled else NullWebhookNotifier()
