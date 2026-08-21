import asyncio
import os
import time
import uuid
from collections.abc import Callable

import httpx

from generation.generation_provider import ProviderError
from provider.gigachat_responses import read_access_token, read_completion
from provider.gigachat_settings import SETTINGS
from shared.exceptions import ConfigurationException

MISSING_CREDENTIALS_MESSAGE = "GIGACHAT_CREDENTIALS environment variable is not set"
CREDENTIALS_ENV_VAR = "GIGACHAT_CREDENTIALS"
CA_BUNDLE_ENV_VAR = "GIGACHAT_CA_BUNDLE"

# Endpoints, timeouts and the trust bundle are configuration, and live in
# gigachat_defaults.toml with an environment override each -- see gigachat_settings.
# Re-exported under their old names because they are what the adapter's own tests
# assert against, and a test that hardcodes the URL it expects proves nothing.
TOKEN_URL = SETTINGS.token_url
COMPLETIONS_URL = SETTINGS.completions_url
SCOPE = SETTINGS.scope
MODEL = SETTINGS.model
CONNECT_TIMEOUT_SECONDS = SETTINGS.connect_timeout
READ_TIMEOUT_SECONDS = SETTINGS.read_timeout
WRITE_TIMEOUT_SECONDS = SETTINGS.write_timeout
POOL_TIMEOUT_SECONDS = SETTINGS.pool_timeout
TOKEN_READ_TIMEOUT_SECONDS = SETTINGS.token_read_timeout
_TOKEN_TTL_SECONDS = SETTINGS.token_ttl
_TOKEN_EXPIRY_MARGIN_SECONDS = SETTINGS.token_expiry_margin


class GigaChatProvider:
    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        credentials = os.environ.get(CREDENTIALS_ENV_VAR)
        if not credentials:
            raise ConfigurationException(MISSING_CREDENTIALS_MESSAGE)
        self._credentials = credentials
        self._verify = SETTINGS.ca_bundle
        # monotonic, not wall-clock: an NTP correction must not make a cached
        # token look older or younger than it is. Injectable so the cache's expiry
        # is testable without sleeping for half an hour.
        self._clock = clock or time.monotonic
        self._token: str | None = None
        self._token_expires_at: float = 0.0
        self._token_lock = asyncio.Lock()
        self._client: httpx.AsyncClient | None = None
        self._client_lock = asyncio.Lock()

    async def _http_client(self) -> httpx.AsyncClient:
        """The one client this provider uses, built on first call and kept.

        It used to be constructed per request, inside `async with`, which threw
        away the connection pool after every call -- so each generation paid a
        fresh TCP connect and a full TLS handshake to a host it had just been
        talking to. Worse, `verify=` here is a *path*: every construction made
        httpx build an SSLContext and read and parse the bundled Russian trust-CA
        PEM off disk. The token cache above was added to save one round-trip per
        generation and was quietly handing the saving back.

        Built lazily rather than in `__init__`: `container/runtime` constructs this
        provider at import, where there is no running event loop, and httpx binds
        its connection pool to the loop that first uses it.

        The lock keeps a burst of concurrent generations on a cold cache from
        building several clients and leaking all but the last. Second waiter
        re-checks inside the lock, exactly as `_fetch_token` does.
        """
        async with self._client_lock:
            if self._client is None:
                self._client = httpx.AsyncClient(
                    verify=self._verify,
                    timeout=httpx.Timeout(
                        connect=CONNECT_TIMEOUT_SECONDS,
                        read=READ_TIMEOUT_SECONDS,
                        write=WRITE_TIMEOUT_SECONDS,
                        pool=POOL_TIMEOUT_SECONDS,
                    ),
                )
            return self._client

    async def aclose(self) -> None:
        """Close the pooled connections. Called from the app's lifespan shutdown.

        Idempotent, and safe on a provider that never served a request: a process
        that exits without this leaves sockets for the OS to reap and httpx warns
        about an unclosed client, which is noise in the log that outlives the run
        that caused it.
        """
        async with self._client_lock:
            if self._client is not None:
                await self._client.aclose()
                self._client = None

    async def generate(self, prompt: str) -> str:
        """Post the prompt this adapter was handed, and return the completion.

        It composes nothing. The prompt is built once, in the domain
        (`generation/prompt_template.py`), because a second composer here was free
        to drift from it — and did: the domain's реферат template and its
        invented-sources ban never reached the model while this method wrote its
        own f-string from the entity.
        """
        try:
            token = await self._fetch_token()
            client = await self._http_client()
            response = await client.post(
                COMPLETIONS_URL,
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "model": MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            return read_completion(response)
        except httpx.HTTPError as error:
            raise ProviderError(str(error)) from error

    async def _fetch_token(self) -> str:
        """Return a valid OAuth token, minting one only when there isn't one.

        The token is good for ~30 minutes, and this provider now lives for the
        life of the process (container/runtime builds it once), so caching it
        turns two HTTP round-trips per generation into one. Every generate() used
        to pay the OAuth handshake before it could even ask for a completion.

        The lock keeps a burst of concurrent generations from each minting their
        own token on a cold cache. The second waiter re-checks inside the lock and
        finds the first one's token.
        """
        async with self._token_lock:
            if self._token is not None and self._clock() < self._token_expires_at:
                return self._token
            self._token, self._token_expires_at = await self._mint_token()
            return self._token

    async def _mint_token(self) -> tuple[str, float]:
        try:
            client = await self._http_client()
            response = await client.post(
                TOKEN_URL,
                headers={
                    "Authorization": f"Basic {self._credentials}",
                    "RqUID": str(uuid.uuid4()),
                },
                data={"scope": SCOPE},
                # Overrides the client's long read budget for this one call. The
                # completion needs minutes; an OAuth handshake that has not
                # answered in fifteen seconds is not going to.
                timeout=TOKEN_READ_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            token = read_access_token(response)
        except httpx.HTTPError as error:
            raise ProviderError(str(error)) from error
        # Expiry comes from our own clock plus a conservative TTL, not from the
        # response's expires_at: that is a remote value in remote units, and
        # trusting it means a clock skew or a format change silently produces a
        # token we consider valid and the server does not. The margin makes the
        # cache give up slightly early, which costs one extra handshake and never
        # an auth failure mid-generation.
        return token, self._clock() + _TOKEN_TTL_SECONDS - _TOKEN_EXPIRY_MARGIN_SECONDS
