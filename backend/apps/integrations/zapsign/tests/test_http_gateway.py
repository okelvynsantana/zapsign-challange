"""T040 — `HttpZapSignGateway` contract tests (contracts/zapsign-gateway.md).

TDD-critical (Constitution Principle II): this is the integration seam most likely to
break in production. Every ZapSign response shape is pinned here against `respx`; the
suite never touches the real sandbox.
"""

import json
import logging

import httpx
import pytest
import respx

from apps.integrations.config import ZapSignConfig
from apps.integrations.zapsign.client import HttpZapSignGateway
from apps.integrations.zapsign.gateway import (
    ZapSignCreateRequest,
    ZapSignError,
    ZapSignSignerInput,
)

BASE_URL = "https://sandbox.example.test/api/v1"
API_TOKEN = "zapsign-secret-token-3f9a"

CREATE_RESPONSE = {
    "open_id": 123456,
    "token": "zapsign-doc-token",
    "status": "pending",
    "external_id": "ref-1",
    "signers": [
        {
            "name": "Ana Souza",
            "email": "ana@example.com",
            "token": "signer-token-1",
            "status": "new",
            "external_id": None,
        }
    ],
}


@pytest.fixture
def gateway() -> HttpZapSignGateway:
    return HttpZapSignGateway(ZapSignConfig(base_url=BASE_URL, timeout_seconds=1.0))


@pytest.fixture
def create_request() -> ZapSignCreateRequest:
    return ZapSignCreateRequest(
        api_token=API_TOKEN,
        name="Contrato X",
        pdf_url="https://files.example.test/contrato.pdf",
        signers=(ZapSignSignerInput(name="Ana Souza", email="ana@example.com"),),
        external_id="ref-1",
    )


@respx.mock
def test_create_document_posts_the_documented_payload(
    gateway: HttpZapSignGateway, create_request: ZapSignCreateRequest
) -> None:
    route = respx.post(f"{BASE_URL}/docs/").mock(
        return_value=httpx.Response(200, json=CREATE_RESPONSE)
    )

    gateway.create_document(create_request)

    assert route.call_count == 1
    sent = route.calls.last.request
    assert sent.headers["Authorization"] == f"Bearer {API_TOKEN}"
    body = json.loads(sent.content)
    assert body["name"] == "Contrato X"
    assert body["url_pdf"] == "https://files.example.test/contrato.pdf"
    assert body["external_id"] == "ref-1"
    assert body["signers"] == [{"name": "Ana Souza", "email": "ana@example.com"}]


@respx.mock
def test_a_200_is_parsed_into_a_typed_result(
    gateway: HttpZapSignGateway, create_request: ZapSignCreateRequest
) -> None:
    respx.post(f"{BASE_URL}/docs/").mock(return_value=httpx.Response(200, json=CREATE_RESPONSE))

    result = gateway.create_document(create_request)

    assert result.open_id == 123456
    assert result.token == "zapsign-doc-token"
    assert result.status == "pending"
    assert result.external_id == "ref-1"
    (signer,) = result.signers
    assert (signer.email, signer.token, signer.status) == (
        "ana@example.com",
        "signer-token-1",
        "new",
    )


@respx.mock
def test_a_read_timeout_becomes_a_typed_timeout_error(
    gateway: HttpZapSignGateway, create_request: ZapSignCreateRequest
) -> None:
    respx.post(f"{BASE_URL}/docs/").mock(side_effect=httpx.ReadTimeout("too slow"))

    with pytest.raises(ZapSignError) as exc_info:
        gateway.create_document(create_request)

    assert exc_info.value.kind == "timeout"


@respx.mock
def test_a_connection_error_becomes_a_typed_connection_error(
    gateway: HttpZapSignGateway, create_request: ZapSignCreateRequest
) -> None:
    respx.post(f"{BASE_URL}/docs/").mock(side_effect=httpx.ConnectError("no route"))

    with pytest.raises(ZapSignError) as exc_info:
        gateway.create_document(create_request)

    assert exc_info.value.kind == "connection"


@respx.mock
def test_a_401_becomes_an_auth_error(
    gateway: HttpZapSignGateway, create_request: ZapSignCreateRequest
) -> None:
    respx.post(f"{BASE_URL}/docs/").mock(return_value=httpx.Response(401, json={"detail": "bad"}))

    with pytest.raises(ZapSignError) as exc_info:
        gateway.create_document(create_request)

    assert exc_info.value.kind == "auth"
    assert exc_info.value.status_code == 401


@respx.mock
def test_a_500_becomes_an_http_status_error(
    gateway: HttpZapSignGateway, create_request: ZapSignCreateRequest
) -> None:
    respx.post(f"{BASE_URL}/docs/").mock(return_value=httpx.Response(500, text="boom"))

    with pytest.raises(ZapSignError) as exc_info:
        gateway.create_document(create_request)

    assert exc_info.value.kind == "http_status"
    assert exc_info.value.status_code == 500


@respx.mock
def test_a_malformed_body_becomes_an_invalid_response_error(
    gateway: HttpZapSignGateway, create_request: ZapSignCreateRequest
) -> None:
    respx.post(f"{BASE_URL}/docs/").mock(return_value=httpx.Response(200, json={"nope": True}))

    with pytest.raises(ZapSignError) as exc_info:
        gateway.create_document(create_request)

    assert exc_info.value.kind == "invalid_response"


@respx.mock
def test_the_api_token_never_reaches_a_log_line_or_an_exception(
    gateway: HttpZapSignGateway,
    create_request: ZapSignCreateRequest,
    caplog: pytest.LogCaptureFixture,
) -> None:
    respx.post(f"{BASE_URL}/docs/").mock(
        return_value=httpx.Response(401, json={"detail": f"token {API_TOKEN} rejected"})
    )

    with caplog.at_level(logging.DEBUG), pytest.raises(ZapSignError) as exc_info:
        gateway.create_document(create_request)

    assert API_TOKEN not in str(exc_info.value)
    assert API_TOKEN not in exc_info.value.message
    assert API_TOKEN not in caplog.text


@respx.mock
def test_get_document_returns_the_current_status_and_signers(
    gateway: HttpZapSignGateway,
) -> None:
    respx.get(f"{BASE_URL}/docs/zapsign-doc-token/").mock(
        return_value=httpx.Response(
            200,
            json={
                "open_id": 123456,
                "token": "zapsign-doc-token",
                "status": "signed",
                "signers": [
                    {
                        "name": "Ana Souza",
                        "email": "ana@example.com",
                        "token": "signer-token-1",
                        "status": "signed",
                        "external_id": None,
                    }
                ],
            },
        )
    )

    result = gateway.get_document(api_token=API_TOKEN, doc_token="zapsign-doc-token")

    assert result.status == "signed"
    assert result.signers[0].status == "signed"
