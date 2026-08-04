"""Shared scaffolding for the GigaChatProvider tests.

Extracted so the generate/error tests and the token-caching tests are separate
files under the 200-line limit, rather than one file that had grown to hold both.
Named _fixtures rather than conftest: these are helpers the tests call, not pytest
fixtures they request, and a conftest would make them ambient.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

from document.document_type import DOKLAD
from generation.generation import Generation
from generation.prompt_template import PromptRequest
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


def build_generation(document_type: str = DOKLAD):
    """The entity the provider tests drive `generate()` with.

    `document_type` is a parameter with the domain's own `DOKLAD` as the default
    rather than a retyped `"доклад"` literal: a hand-typed copy of a domain
    constant in scaffolding is exactly what the prompt-agreement test exists to
    eliminate on the prompt side.
    """
    return Generation.create(
        owner_id=uuid.uuid4(),
        topic="Космос",
        volume_pages=3,
        requirements=None,
        extra_wishes=None,
        document_type=document_type,
    )


def build_doklad_generation():
    """A generation whose type is доклад, and which proves it before returning.

    The prompt-agreement test's scope is доклад **by decision, not by accident**:
    the provider appends no source ban while `build_prompt` appends one for every
    type outside `_BAN_DEFERRED`, so the two composers are comparable over доклад
    and nowhere else. Riding on `build_generation()`'s default would leave that
    decision expressed only in a docstring, and four other test files share that
    default -- any of them could legitimately retarget it, silently re-scoping the
    agreement assertion into a red that has no defect behind it, whose cheapest
    escape is to widen `_BAN_DEFERRED` (i.e. to unban the other three types).

    The guard lives here rather than in the test class so a default change breaks
    loudly at the scaffolding instead of quietly changing what the test covers.
    """
    generation = build_generation(document_type=DOKLAD)
    assert generation.document_type == DOKLAD, (
        "the prompt-agreement scope is доклад by decision; see this function's docstring"
    )
    return generation


def request_from(generation) -> PromptRequest:
    """The domain composer's input, read off the same entity the provider saw.

    Reading the fields from `generation` rather than restating them is what keeps
    both sides of the agreement assertion live: a scaffolding change moves both,
    and only a genuine divergence between the two composers can separate them.
    Lives beside `build_generation` -- its mirror -- so a change to the entity's
    fields is visibly paired with the helper that reads them back.
    """
    return PromptRequest(
        document_type=generation.document_type,
        topic=generation.topic,
        volume_pages=generation.volume_pages,
    )


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
