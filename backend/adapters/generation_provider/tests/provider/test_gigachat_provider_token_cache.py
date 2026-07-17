import asyncio

from gigachat_fixtures import (
    build_generation,
    completions_payload,
    json_response,
    patch_async_client,
    posted_urls,
    set_credentials,
    token_payload,
)
from provider.gigachat_provider import (
    _TOKEN_TTL_SECONDS,
    COMPLETIONS_URL,
    TOKEN_URL,
    GigaChatProvider,
)


class TestTokenCaching:
    """The OAuth token is minted once and reused until it nears expiry.

    The provider is built once per process (container/runtime), so a token good
    for ~30 minutes should not be re-fetched per generation -- that doubled the
    request count and the latency of every generate().
    """

    async def test_should_mint_the_token_once_across_two_generations(self, monkeypatch, mocker):
        set_credentials(monkeypatch)
        client = patch_async_client(
            mocker,
            [
                json_response(token_payload()),
                json_response(completions_payload()),
                json_response(completions_payload()),
            ],
        )
        provider = GigaChatProvider()

        await provider.generate(build_generation())
        await provider.generate(build_generation())

        # One token + two completions, not one token per generation.
        assert posted_urls(client) == [TOKEN_URL, COMPLETIONS_URL, COMPLETIONS_URL]

    async def test_should_mint_a_fresh_token_once_the_cached_one_expires(self, monkeypatch, mocker):
        set_credentials(monkeypatch)
        client = patch_async_client(
            mocker,
            [
                json_response(token_payload()),
                json_response(completions_payload()),
                json_response(token_payload()),
                json_response(completions_payload()),
            ],
        )
        now = [1000.0]
        provider = GigaChatProvider(clock=lambda: now[0])

        await provider.generate(build_generation())
        now[0] += _TOKEN_TTL_SECONDS  # past the cached token's margin-adjusted expiry
        await provider.generate(build_generation())

        assert posted_urls(client) == [TOKEN_URL, COMPLETIONS_URL, TOKEN_URL, COMPLETIONS_URL], (
            "an expired token must be re-minted, not reused"
        )

    async def test_should_reuse_a_token_that_is_still_inside_its_ttl(self, monkeypatch, mocker):
        set_credentials(monkeypatch)
        client = patch_async_client(
            mocker,
            [
                json_response(token_payload()),
                json_response(completions_payload()),
                json_response(completions_payload()),
            ],
        )
        now = [1000.0]
        provider = GigaChatProvider(clock=lambda: now[0])

        await provider.generate(build_generation())
        now[0] += 60  # a minute later: well inside the ~30 minute TTL
        await provider.generate(build_generation())

        assert posted_urls(client).count(TOKEN_URL) == 1

    async def test_should_mint_once_when_two_generations_race_on_a_cold_cache(
        self, monkeypatch, mocker
    ):
        set_credentials(monkeypatch)
        client = patch_async_client(
            mocker,
            [
                json_response(token_payload()),
                json_response(completions_payload()),
                json_response(completions_payload()),
            ],
        )
        provider = GigaChatProvider()

        await asyncio.gather(
            provider.generate(build_generation()), provider.generate(build_generation())
        )

        assert posted_urls(client).count(TOKEN_URL) == 1, (
            "a burst on a cold cache must mint one token. Without the lock each "
            "concurrent generation mints its own."
        )
