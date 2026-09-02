"""The one thing both geolocation suites need: a client that opens no socket.

`httpx.MockTransport` answers every request in-process, the same idiom
`test_yandex_oauth_provider.py` uses. It lives here rather than in either test
module because both need it and neither owns it.
"""

import httpx
import pytest
from geolocation import http_geolocation
from geolocation.http_geolocation import HttpGeolocation

_REAL_ASYNC_CLIENT = httpx.AsyncClient


@pytest.fixture
def answering(monkeypatch):
    """Build a client whose every request is answered by the given handler.

    The requests that went out are recorded on `client.requests`, because "asked
    once" and "the token travels as a query credential" are properties of the wire
    traffic and there is nowhere else to read them from.
    """

    def build(handler) -> HttpGeolocation:
        seen: list[httpx.Request] = []

        def recording(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return handler(request)

        def factory(*args, **kwargs):  # noqa: ARG001 -- httpx client shape
            return _REAL_ASYNC_CLIENT(transport=httpx.MockTransport(recording))

        monkeypatch.setattr(http_geolocation.httpx, "AsyncClient", factory)
        client = HttpGeolocation(
            base_url="https://lookup.local/", token="SECRET", timeout_seconds=1.5
        )
        client.requests = seen  # type: ignore[attr-defined] -- test handle on what went out
        return client

    return build


@pytest.fixture
def ok():
    """A handler answering 200 with the given JSON body."""

    def build(body: object):
        return lambda _request: httpx.Response(200, json=body)

    return build
