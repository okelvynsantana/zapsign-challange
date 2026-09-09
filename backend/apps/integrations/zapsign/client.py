"""`httpx` implementation of the ZapSign gateway.

The only module in the codebase that knows ZapSign's URLs and payload shape. Every failure
mode is mapped onto `ZapSignError` so callers never see an `httpx` type, and the account
token is redacted from every message and log line before it can escape.
"""

import json
from typing import Any

import httpx

from apps.core.logging import log_gateway_call, redact
from apps.integrations.config import ZapSignConfig
from apps.integrations.zapsign.gateway import (
    ZapSignCreateRequest,
    ZapSignCreateResult,
    ZapSignDocumentStatus,
    ZapSignError,
    ZapSignGateway,
    ZapSignSignerResult,
)

__all__ = ["HttpZapSignGateway"]

HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
MAX_ERROR_BODY_CHARS = 300


class HttpZapSignGateway(ZapSignGateway):
    """Talks to the ZapSign REST API over HTTP with bounded timeouts."""

    def __init__(self, config: ZapSignConfig) -> None:
        self._config = config

    # -- public interface --------------------------------------------------------------

    @log_gateway_call(provider="zapsign", operation="create_document")
    def create_document(self, request: ZapSignCreateRequest) -> ZapSignCreateResult:
        payload: dict[str, Any] = {
            "name": request.name,
            "url_pdf": request.pdf_url,
            "signers": [{"name": signer.name, "email": signer.email} for signer in request.signers],
        }
        if request.external_id:
            payload["external_id"] = request.external_id

        body = self._request(
            "POST",
            "/docs/",
            api_token=request.api_token,
            json_payload=payload,
        )
        return self._parse_create_result(body, api_token=request.api_token)

    @log_gateway_call(provider="zapsign", operation="get_document")
    def get_document(self, *, api_token: str, doc_token: str) -> ZapSignDocumentStatus:
        body = self._request("GET", f"/docs/{doc_token}/", api_token=api_token)
        try:
            return ZapSignDocumentStatus(
                open_id=int(body["open_id"]),
                token=str(body["token"]),
                status=str(body.get("status") or ""),
                signers=self._parse_signers(body.get("signers")),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise self._invalid_response(exc, api_token) from exc

    # -- internals ---------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        api_token: str,
        json_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self._config.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

        try:
            response = httpx.request(
                method,
                url,
                headers=headers,
                json=json_payload,
                timeout=self._config.timeout_seconds,
                verify=self._config.verify_ssl,
            )
        except httpx.TimeoutException as exc:
            raise ZapSignError("timeout", self._safe(str(exc), api_token)) from exc
        except httpx.HTTPError as exc:
            raise ZapSignError("connection", self._safe(str(exc), api_token)) from exc

        self._raise_for_status(response, api_token)

        try:
            body = response.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise self._invalid_response(exc, api_token) from exc

        if not isinstance(body, dict):
            raise ZapSignError("invalid_response", "ZapSign returned a non-object body.")
        return body

    def _raise_for_status(self, response: httpx.Response, api_token: str) -> None:
        if response.is_success:
            return

        detail = self._safe(response.text[:MAX_ERROR_BODY_CHARS], api_token)
        if response.status_code in (HTTP_UNAUTHORIZED, HTTP_FORBIDDEN):
            # The stored Company.api_token is wrong — retryable once it is fixed.
            raise ZapSignError(
                "auth",
                f"ZapSign rejected the account credential: {detail}",
                status_code=response.status_code,
            )
        raise ZapSignError(
            "http_status",
            f"ZapSign returned HTTP {response.status_code}: {detail}",
            status_code=response.status_code,
        )

    def _parse_create_result(self, body: dict[str, Any], *, api_token: str) -> ZapSignCreateResult:
        try:
            return ZapSignCreateResult(
                open_id=int(body["open_id"]),
                token=str(body["token"]),
                status=str(body.get("status") or ""),
                external_id=body.get("external_id"),
                signers=self._parse_signers(body.get("signers")),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise self._invalid_response(exc, api_token) from exc

    @staticmethod
    def _parse_signers(raw: Any) -> tuple[ZapSignSignerResult, ...]:
        if not isinstance(raw, list):
            return ()
        return tuple(
            ZapSignSignerResult(
                name=str(item.get("name") or ""),
                email=str(item.get("email") or ""),
                token=item.get("token"),
                status=item.get("status"),
                external_id=item.get("external_id"),
            )
            for item in raw
            if isinstance(item, dict)
        )

    @staticmethod
    def _safe(text: str, api_token: str) -> str:
        """Never let the account credential travel into a message or a log line."""
        return redact(text, [api_token])

    def _invalid_response(self, exc: Exception, api_token: str) -> ZapSignError:
        return ZapSignError(
            "invalid_response",
            f"ZapSign returned an unparseable response: {self._safe(str(exc), api_token)}",
        )
