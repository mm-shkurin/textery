import asyncio
import os
import time
import uuid
from collections.abc import Callable

import httpx

from generation.generation_provider import ProviderError
from provider.gigachat_responses import read_access_token, read_completion
from shared.exceptions import ConfigurationException

MISSING_CREDENTIALS_MESSAGE = "GIGACHAT_CREDENTIALS environment variable is not set"
# GigaChat's OAuth tokens last ~30 minutes. The margin is subtracted so the cache
# expires before the server's copy does.
_TOKEN_TTL_SECONDS = 30 * 60
_TOKEN_EXPIRY_MARGIN_SECONDS = 60
TOKEN_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
COMPLETIONS_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
SCOPE = "GIGACHAT_API_PERS"
CREDENTIALS_ENV_VAR = "GIGACHAT_CREDENTIALS"
CA_BUNDLE_ENV_VAR = "GIGACHAT_CA_BUNDLE"
# Split, where a single `timeout=30` scalar used to set all four httpx phases at
# once. Connect and read want very different numbers here: failing to reach the
# host is answered in seconds and retrying is cheap, while a completion for a
# multi-page document is the model composing text and legitimately takes minutes.
# Under one 30-second scalar a slow-but-working generation was indistinguishable
# from an outage -- three attempts, three timeouts, and a row written `failed`
# for a provider that was answering the whole time.
CONNECT_TIMEOUT_SECONDS = 10.0
READ_TIMEOUT_SECONDS = 180.0
WRITE_TIMEOUT_SECONDS = 30.0
POOL_TIMEOUT_SECONDS = 10.0
# The token exchange is a small, fast call and gets its own read budget: waiting
# three minutes on an OAuth handshake only delays the real failure.
TOKEN_READ_TIMEOUT_SECONDS = 15.0
# GigaChat's TLS cert chains to the Russian Minsvyaz trust CA, which is not in
# most system trust stores. Bundled PEM fetched from gu-st.ru — GIGACHAT_CA_BUNDLE
# overrides it, but this is the working default rather than disabling verification.
_DEFAULT_CA_BUNDLE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "certs",
    "russiantrustedca.pem",
)


class GigaChatProvider:
    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        credentials = os.environ.get(CREDENTIALS_ENV_VAR)
        if not credentials:
            raise ConfigurationException(MISSING_CREDENTIALS_MESSAGE)
        self._credentials = credentials
        self._verify = os.environ.get(CA_BUNDLE_ENV_VAR, _DEFAULT_CA_BUNDLE)
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
                    "model": "GigaChat",
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
