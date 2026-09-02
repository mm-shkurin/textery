"""How the client is built, and how it lets go.

Split from `test_http_geolocation.py` to keep both under the 200-line cap
(`.claude/rules/coding-rules.md`). The division is by kind: that file asserts
what the client ANSWERS, this one asserts what the deployment BUILDS and what
the process releases.
"""

import httpx
import pytest
from geolocation.http_geolocation import (
    DEFAULT_TIMEOUT_SECONDS,
    GEOLOCATION_TIMEOUT_ENV_VAR,
    GEOLOCATION_TOKEN_ENV_VAR,
    GEOLOCATION_URL_ENV_VAR,
    HttpGeolocation,
    create_geolocation,
)


class TestUnconfiguredIsALegitimateState:
    """§3.1 — a missing configuration is one unset column, not a boot failure."""

    @pytest.mark.parametrize("value", ["", "   "], ids=["unset", "blank"])
    def test_no_base_url_answers_none_instead_of_raising(self, value, monkeypatch):
        monkeypatch.setenv(GEOLOCATION_URL_ENV_VAR, value)

        assert create_geolocation() is None

    def test_a_configured_deployment_gets_a_client_with_the_declared_timeout(self, monkeypatch):
        monkeypatch.setenv(GEOLOCATION_URL_ENV_VAR, "https://lookup.local")
        monkeypatch.setenv(GEOLOCATION_TOKEN_ENV_VAR, "T0KEN")
        monkeypatch.setenv(GEOLOCATION_TIMEOUT_ENV_VAR, "0.25")

        client = create_geolocation()

        assert client is not None
        assert client._token == "T0KEN"
        assert client._client.timeout.read == 0.25

    def test_an_unset_timeout_falls_back_to_the_declared_default(self, monkeypatch):
        monkeypatch.setenv(GEOLOCATION_URL_ENV_VAR, "https://lookup.local")
        monkeypatch.delenv(GEOLOCATION_TIMEOUT_ENV_VAR, raising=False)

        client = create_geolocation()

        assert client is not None
        assert client._client.timeout.read == DEFAULT_TIMEOUT_SECONDS

    def test_the_timeout_is_total_rather_than_connect_only(self, monkeypatch):
        """§2.3 — the shape that hangs a request is one that connects and never answers."""
        monkeypatch.setenv(GEOLOCATION_URL_ENV_VAR, "https://lookup.local")
        monkeypatch.setenv(GEOLOCATION_TIMEOUT_ENV_VAR, "0.5")

        client = create_geolocation()

        assert client is not None
        timeout = client._client.timeout
        assert (timeout.connect, timeout.read, timeout.write, timeout.pool) == (0.5, 0.5, 0.5, 0.5)


class TestTheCredentialItSends:
    def test_an_unset_token_sends_no_credential_rather_than_an_empty_one(self):
        client = HttpGeolocation(base_url="https://lookup.local", token="", timeout_seconds=1.5)

        assert client._credentials() == {}

    def test_a_configured_token_is_sent(self):
        client = HttpGeolocation(
            base_url="https://lookup.local", token="T0KEN", timeout_seconds=1.5
        )

        assert client._credentials() == {"token": "T0KEN"}


class TestItReturnsItsConnections:
    """§2.4 — one client for the process; a failing lookup must not leak a socket."""

    async def test_closing_closes_the_underlying_client(self, monkeypatch):
        from geolocation import http_geolocation

        real = httpx.AsyncClient

        def factory(*args, **kwargs):  # noqa: ARG001 -- httpx client shape
            return real(transport=httpx.MockTransport(lambda _r: httpx.Response(200, json={})))

        monkeypatch.setattr(http_geolocation.httpx, "AsyncClient", factory)
        client = HttpGeolocation(base_url="https://lookup.local", token="", timeout_seconds=1.5)

        await client.aclose()

        assert client._client.is_closed
