"""Shared scaffolding for the GigaChatProvider tests.

Extracted so the generate/error tests and the token-caching tests are separate
files under the 200-line limit, rather than one file that had grown to hold both.
Named _fixtures rather than conftest: these are helpers the tests call, not pytest
fixtures they request, and a conftest would make them ambient.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

from generation.generation import Generation
from provider.gigachat_provider import CA_BUNDLE_ENV_VAR, CREDENTIALS_ENV_VAR

ACCESS_TOKEN = "tok-abc-123"
GENERATED_CONTENT = "Готовый доклад про космос."
CREDENTIALS = "dGVzdDp0ZXN0"


def json_response(payload):
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json = MagicMock(return_value=payload)
    return response


def non_json_response(message: str = "Expecting value: line 1 column 1"):
    """A 200 whose body will not parse -- what a proxy's HTML error page looks like."""
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json = MagicMock(side_effect=ValueError(message))
    return response


def token_payload():
    return {"access_token": ACCESS_TOKEN}


def completions_payload():
    return {"choices": [{"message": {"content": GENERATED_CONTENT}}]}


def patch_async_client(mocker, post_side_effect):
    """Stand in for the provider's single pooled client.

    No `__aenter__`/`__aexit__` doubles any more: the provider builds one client
    and keeps it rather than entering `async with` per request, so a context
    manager here would be scaffolding for a call that no longer happens. The
    returned mock is the client itself, and the tests' assertions on
    `client.post` are unchanged.
    """
    client = MagicMock()
    client.post = AsyncMock(side_effect=post_side_effect)
    client.aclose = AsyncMock(return_value=None)
    mocker.patch("provider.gigachat_provider.httpx.AsyncClient", return_value=client)
    return client


def build_generation():
    return Generation.create(
        owner_id=uuid.uuid4(),
        topic="Космос",
        volume_pages=3,
        requirements=None,
        extra_wishes=None,
        document_type="доклад",
    )


def set_credentials(monkeypatch):
    monkeypatch.setenv(CREDENTIALS_ENV_VAR, CREDENTIALS)
    monkeypatch.setenv(CA_BUNDLE_ENV_VAR, "dummy-ca-bundle")


def posted_urls(client) -> list[str]:
    return [call.args[0] for call in client.post.await_args_list]
