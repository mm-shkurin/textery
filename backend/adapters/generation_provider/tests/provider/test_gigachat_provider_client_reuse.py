import httpx

from gigachat_fixtures import (
    PROMPT,
    completions_payload,
    json_response,
    patch_async_client,
    set_credentials,
    token_payload,
)
from provider.gigachat_provider import (
    CONNECT_TIMEOUT_SECONDS,
    READ_TIMEOUT_SECONDS,
    TOKEN_READ_TIMEOUT_SECONDS,
    GigaChatProvider,
)


def _two_generations_worth(count: int):
    return [json_response(token_payload())] + [
        json_response(completions_payload()) for _ in range(count)
    ]


class TestHttpClientReuse:
    """One pooled client for the life of the provider, not one per request.

    The provider is built once per process (`container/runtime`). Building a
    client per call discarded the connection pool after every generation -- a
    fresh TCP connect and full TLS handshake each time -- and, because `verify=`
    is a path, made httpx read and parse the trust-CA PEM off disk on every
    construction. The token cache exists to save one round-trip per generation;
    this is what stops that saving being handed straight back.
    """

    async def test_should_build_the_client_once_across_two_generations(self, monkeypatch, mocker):
        set_credentials(monkeypatch)
        patch_async_client(mocker, _two_generations_worth(2))
        provider = GigaChatProvider()

        await provider.generate(PROMPT)
        await provider.generate(PROMPT)

        assert httpx.AsyncClient.call_count == 1

    async def test_should_not_build_a_client_before_the_first_request(self, monkeypatch, mocker):
        """Lazily, not in `__init__`.

        `container/runtime` constructs the provider at import time, where no event
        loop is running yet, and httpx binds its pool to the loop that first uses
        it. Constructing eagerly would bind the pool to the wrong loop -- or to
        none.
        """
        set_credentials(monkeypatch)
        patch_async_client(mocker, _two_generations_worth(1))

        GigaChatProvider()

        assert httpx.AsyncClient.call_count == 0


class TestConfiguredTimeouts:
    async def test_should_separate_the_connect_and_read_budgets(self, monkeypatch, mocker):
        """A single scalar set all four httpx phases to the same 30 seconds.

        Connect and read want very different numbers: an unreachable host is
        answered in seconds, while a multi-page completion is the model composing
        text. Under one scalar a slow-but-working generation looked exactly like
        an outage, and `GenerateDocument` wrote the row `failed` after three
        timeouts against a provider that was answering the whole time.
        """
        set_credentials(monkeypatch)
        patch_async_client(mocker, _two_generations_worth(1))
        provider = GigaChatProvider()

        await provider.generate(PROMPT)

        timeout = httpx.AsyncClient.call_args.kwargs["timeout"]
        assert timeout.connect == CONNECT_TIMEOUT_SECONDS
        assert timeout.read == READ_TIMEOUT_SECONDS
        assert timeout.read > timeout.connect

    async def test_should_give_the_token_call_its_own_shorter_read_budget(
        self, monkeypatch, mocker
    ):
        """Waiting three minutes on an OAuth handshake only delays the failure."""
        set_credentials(monkeypatch)
        client = patch_async_client(mocker, _two_generations_worth(1))
        provider = GigaChatProvider()

        await provider.generate(PROMPT)

        token_call = client.post.await_args_list[0]
        assert token_call.kwargs["timeout"] == TOKEN_READ_TIMEOUT_SECONDS
        assert TOKEN_READ_TIMEOUT_SECONDS < READ_TIMEOUT_SECONDS


class TestAclose:
    async def test_should_close_the_pooled_client(self, monkeypatch, mocker):
        set_credentials(monkeypatch)
        client = patch_async_client(mocker, _two_generations_worth(1))
        provider = GigaChatProvider()
        await provider.generate(PROMPT)

        await provider.aclose()

        client.aclose.assert_awaited_once()

    async def test_should_be_safe_on_a_provider_that_never_served_a_request(
        self, monkeypatch, mocker
    ):
        """The shutdown path calls this unconditionally, including on a process
        that booted and exited without a single generation.
        """
        set_credentials(monkeypatch)
        patch_async_client(mocker, [])

        await GigaChatProvider().aclose()

    async def test_should_be_idempotent(self, monkeypatch, mocker):
        set_credentials(monkeypatch)
        client = patch_async_client(mocker, _two_generations_worth(1))
        provider = GigaChatProvider()
        await provider.generate(PROMPT)

        await provider.aclose()
        await provider.aclose()

        client.aclose.assert_awaited_once()
