"""Per-request structured access logging (Constitution Principle V, FR-029)."""

import logging
import time
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from apps.core.logging import correlation_id_var, new_correlation_id

__all__ = ["CORRELATION_ID_HEADER", "RequestTimingLogger"]

CORRELATION_ID_HEADER = "X-Correlation-ID"

request_logger = logging.getLogger("api.request")


class RequestTimingLogger:
    """Log one JSON entry per request with method, path, status and elapsed time.

    The correlation id is taken from the inbound ``X-Correlation-ID`` header when present
    (so a caller can stitch its own traces to ours) and generated otherwise; it is echoed
    back on the response.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or new_correlation_id()
        token = correlation_id_var.set(correlation_id)
        started = time.perf_counter()

        # The access log is emitted while the context variable is still set, so this
        # record — and anything logged during the request — carries the same id.
        try:
            response = self.get_response(request)
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            request_logger.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.path,
                    "status_code": response.status_code,
                    "elapsed_ms": elapsed_ms,
                    "correlation_id": correlation_id,
                },
            )
        finally:
            correlation_id_var.reset(token)

        response[CORRELATION_ID_HEADER] = correlation_id
        return response
