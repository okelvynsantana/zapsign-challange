"""Structured logging: JSON formatting, request correlation, and gateway call timing.

Constitution Principle V / FR-029: every external-dependency call and every primary route
emits one structured entry carrying outcome status and elapsed time. Secrets never appear
in a log record — :func:`redact` is applied to anything a gateway passes through here.
"""

import logging
import time
import uuid
from collections.abc import Callable, Iterable
from contextvars import ContextVar
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from pythonjsonlogger.json import JsonFormatter as BaseJsonFormatter

__all__ = [
    "CorrelationIdFilter",
    "JsonFormatter",
    "correlation_id_var",
    "log_gateway_call",
    "new_correlation_id",
    "redact",
]

P = ParamSpec("P")
R = TypeVar("R")

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="-")

#: Substrings that mark a value as sensitive wherever it appears in log extras.
SENSITIVE_KEY_HINTS: frozenset[str] = frozenset(
    {"token", "secret", "password", "api_key", "apikey", "authorization"}
)

REDACTED = "***redacted***"
MIN_REDACTABLE_LENGTH = 4


def new_correlation_id() -> str:
    """Return a fresh correlation id for one inbound request."""
    return uuid.uuid4().hex


def redact(text: str, secrets: Iterable[str] = ()) -> str:
    """Replace every occurrence of ``secrets`` in ``text`` with a redaction marker."""
    result = text
    for secret in secrets:
        if secret and len(secret) >= MIN_REDACTABLE_LENGTH:
            result = result.replace(secret, REDACTED)
    return result


class CorrelationIdFilter(logging.Filter):
    """Attach the current request's correlation id to every record.

    A record that already carries one (passed through `extra=`) keeps it: the emitting
    code knows which request it belongs to, and the context variable may already have been
    reset by the time the handler runs.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "correlation_id", None):
            record.correlation_id = correlation_id_var.get()
        return True


class JsonFormatter(BaseJsonFormatter):
    """JSON formatter with a stable envelope (timestamp, level, logger, message)."""

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record.setdefault("timestamp", self.formatTime(record, self.datefmt))
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record.setdefault("correlation_id", getattr(record, "correlation_id", "-"))


gateway_logger = logging.getLogger("integrations.gateway")


def log_gateway_call(
    provider: str,
    operation: str,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Log one structured entry per external-dependency call.

    Emits ``provider``, ``operation``, ``outcome`` (``ok``/``error``), ``elapsed_ms`` and,
    on failure, the exception class and its message. The wrapped callable's exception is
    always re-raised — this decorator observes, it never swallows.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            started = time.perf_counter()
            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                gateway_logger.warning(
                    "gateway_call_failed",
                    extra={
                        "provider": provider,
                        "operation": operation,
                        "outcome": "error",
                        "error_class": type(exc).__name__,
                        "error_message": str(exc),
                        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                    },
                )
                raise
            gateway_logger.info(
                "gateway_call",
                extra={
                    "provider": provider,
                    "operation": operation,
                    "outcome": "ok",
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
            return result

        return wrapper

    return decorator
