"""Shared scaffolding for the GigaChatProvider tests.

Extracted so the generate/error tests and the token-caching tests are separate
files under the 200-line limit, rather than one file that had grown to hold both.
Named _fixtures rather than conftest: these are helpers the tests call, not pytest
fixtures they request, and a conftest would make them ambient.
"""

from unittest.mock import AsyncMock, MagicMock

from document.document_type import DOKLAD
from generation.prompt_template import PromptRequest, build_prompt
from provider.gigachat_provider import CA_BUNDLE_ENV_VAR, COMPLETIONS_URL, CREDENTIALS_ENV_VAR

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


# What the provider is handed since scenario 2.1: composed text, not an entity.
# Built by the domain from a real request rather than hand-typed, so it stays the
# shape production actually sends -- but the provider tests assert only that this
# exact string is posted back, never what is in it. What goes into a prompt is the
# domain's claim and is pinned by the prompt goldens; this module's claim is that
# the transport does not touch it.
PROMPT = build_prompt(PromptRequest(document_type=DOKLAD, topic="Космос", volume_pages=3))


def set_credentials(monkeypatch):
    monkeypatch.setenv(CREDENTIALS_ENV_VAR, CREDENTIALS)
    monkeypatch.setenv(CA_BUNDLE_ENV_VAR, "dummy-ca-bundle")


def posted_urls(client) -> list[str]:
    return [call.args[0] for call in client.post.await_args_list]


def posted_completion_messages(client) -> list[dict]:
    """The `messages` list out of the body the provider actually POSTed.

    Read off the `json=` kwarg of the real call -- not a convenience attribute on
    the double -- so what is asserted is the payload that would have gone over the
    wire.

    The call is located **by URL, not by position**. Picking `await_args_list[1]`
    assumes call 2 is the completion; a provider that refreshed an expired token
    mid-flight, or reordered its calls, would hand the wrong call's body back and
    the caller would compare the wrong thing. Requiring exactly one match turns
    both "no completion was posted at all" and "more than one" into a named
    failure here rather than a tuple-unpack ValueError at the call site.
    """
    calls = [call for call in client.post.await_args_list if call.args[0] == COMPLETIONS_URL]
    assert len(calls) == 1, f"expected exactly one POST to {COMPLETIONS_URL}, got {len(calls)}"
    return calls[0].kwargs["json"]["messages"]
