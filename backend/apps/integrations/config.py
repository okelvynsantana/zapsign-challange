"""Typed, env-driven configuration for every external integration.

One frozen dataclass per provider, built once from the environment. Gateways receive their
configuration rather than reading ``os.environ`` or ``django.conf.settings`` themselves, so
they stay unit-testable without patching globals. Defaults match the contract documents.
"""

from dataclasses import dataclass
from functools import lru_cache

from config.settings.env import env_bool, env_int, env_str

__all__ = [
    "AnalysisConfig",
    "IntegrationsConfig",
    "PdfConfig",
    "WebhookConfig",
    "ZapSignConfig",
    "get_integrations_config",
]

DEFAULT_ZAPSIGN_BASE_URL = "https://sandbox.api.zapsign.com.br/api/v1"
DEFAULT_AI_MODEL = "gpt-4o-mini"

DEFAULT_EXPECTED_CLAUSES = (
    "objeto",
    "prazo/vigência",
    "rescisão",
    "multa/penalidade",
    "foro",
    "confidencialidade",
    "pagamento",
    "proteção de dados/LGPD",
)


@dataclass(frozen=True, slots=True)
class ZapSignConfig:
    """``contracts/zapsign-gateway.md`` configuration table."""

    base_url: str = DEFAULT_ZAPSIGN_BASE_URL
    timeout_seconds: float = 10.0
    verify_ssl: bool = True
    use_fake: bool = False

    @classmethod
    def from_env(cls) -> "ZapSignConfig":
        return cls(
            base_url=env_str("ZAPSIGN_BASE_URL", DEFAULT_ZAPSIGN_BASE_URL).rstrip("/"),
            timeout_seconds=float(env_int("ZAPSIGN_TIMEOUT_SECONDS", 10)),
            verify_ssl=env_bool("ZAPSIGN_VERIFY_SSL", True),
            use_fake=env_bool("ZAPSIGN_USE_FAKE", False),
        )


@dataclass(frozen=True, slots=True)
class AnalysisConfig:
    """``contracts/analysis-provider.md`` configuration table."""

    api_key: str = ""
    model: str = DEFAULT_AI_MODEL
    timeout_seconds: float = 15.0
    max_input_chars: int = 60000
    regex_fallback_enabled: bool = True
    expected_clauses: tuple[str, ...] = DEFAULT_EXPECTED_CLAUSES
    use_fake: bool = False

    @classmethod
    def from_env(cls) -> "AnalysisConfig":
        raw_clauses = env_str("AI_EXPECTED_CLAUSES", "")
        clauses = tuple(part.strip() for part in raw_clauses.split(",") if part.strip())
        return cls(
            api_key=env_str("OPENAI_API_KEY", ""),
            model=env_str("AI_MODEL", DEFAULT_AI_MODEL),
            timeout_seconds=float(env_int("AI_TIMEOUT_SECONDS", 15)),
            max_input_chars=env_int("AI_MAX_INPUT_CHARS", 60000),
            regex_fallback_enabled=env_bool("AI_REGEX_FALLBACK_ENABLED", True),
            expected_clauses=clauses or DEFAULT_EXPECTED_CLAUSES,
            use_fake=env_bool("AI_USE_FAKE", False),
        )


@dataclass(frozen=True, slots=True)
class PdfConfig:
    """PDF fetch/extraction limits."""

    fetch_timeout_seconds: float = 10.0
    max_bytes: int = 20 * 1024 * 1024

    @classmethod
    def from_env(cls) -> "PdfConfig":
        return cls(
            fetch_timeout_seconds=float(env_int("PDF_FETCH_TIMEOUT_SECONDS", 10)),
            max_bytes=env_int("PDF_MAX_BYTES", 20971520),
        )


@dataclass(frozen=True, slots=True)
class WebhookConfig:
    """``contracts/webhook-outbound.md`` configuration table."""

    url: str = ""
    secret: str = ""
    timeout_seconds: float = 5.0
    on_every_analysis: bool = False

    @classmethod
    def from_env(cls) -> "WebhookConfig":
        return cls(
            url=env_str("N8N_WEBHOOK_URL", ""),
            secret=env_str("N8N_WEBHOOK_SECRET", ""),
            timeout_seconds=float(env_int("WEBHOOK_TIMEOUT_SECONDS", 5)),
            on_every_analysis=env_bool("WEBHOOK_ON_EVERY_ANALYSIS", False),
        )

    @property
    def enabled(self) -> bool:
        """A blank URL turns the outbound-webhook feature off entirely."""
        return bool(self.url)


@dataclass(frozen=True, slots=True)
class IntegrationsConfig:
    """Every integration's configuration, resolved together."""

    zapsign: ZapSignConfig
    analysis: AnalysisConfig
    pdf: PdfConfig
    webhook: WebhookConfig

    @classmethod
    def from_env(cls) -> "IntegrationsConfig":
        return cls(
            zapsign=ZapSignConfig.from_env(),
            analysis=AnalysisConfig.from_env(),
            pdf=PdfConfig.from_env(),
            webhook=WebhookConfig.from_env(),
        )


@lru_cache(maxsize=1)
def get_integrations_config() -> IntegrationsConfig:
    """Return the process-wide integration configuration (read from the environment once)."""
    return IntegrationsConfig.from_env()
