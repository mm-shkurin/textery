"""Turning the caller's IP address into a country, over HTTP.

Every property of this client exists to keep an outbound network call off the
registration path's critical behaviour (`04_Infrastructure_Tests.md` §2):

* **It never raises.** A dependency that is down, refusing, or answering nonsense
  leaves `registration_country` NULL and the registration whole (§2.1).
* **It is asked once.** No retry loop: a retry against a dependency that is down
  multiplies the latency the registering user waits through by the retry count,
  to obtain a marketing column (§1.3).
* **It is bounded.** A total timeout, not just a connect timeout -- a dependency
  that accepts the connection and then never answers is the shape that actually
  hangs a request (§2.3, §1.4).
* **Its connections are returned.** One `AsyncClient` held for the process, so a
  failing lookup does not leak a socket per registration (§2.4).
* **Its credential never leaves.** The token goes in the request and is never
  logged, never put in a message, never surfaced in a response (§5.6).

Unconfigured is a legitimate deployment state, not a boot failure: `create(...)`
answers `None` and the composition root falls back to `NullGeolocation`
(§3.1).
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

GEOLOCATION_URL_ENV_VAR = "GEOLOCATION_API_URL"
GEOLOCATION_TOKEN_ENV_VAR = "GEOLOCATION_API_TOKEN"
GEOLOCATION_TIMEOUT_ENV_VAR = "GEOLOCATION_TIMEOUT_SECONDS"
DEFAULT_TIMEOUT_SECONDS = 1.5

# The key the response is read from. ip-api, ipinfo and ipapi all spell the
# two-letter country this way; a provider that does not simply yields NULL,
# which is the same outcome as being unreachable and needs no special case.
_COUNTRY_KEY = "countryCode"
_FALLBACK_COUNTRY_KEY = "country"


class HttpGeolocation:
    """`Geolocation` over an HTTP lookup service. Never raises, never retries."""

    def __init__(self, base_url: str, token: str, timeout_seconds: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._client = httpx.AsyncClient(timeout=timeout_seconds)

    async def country_of(self, ip_address: str | None) -> str | None:
        if not ip_address:
            return None
        try:
            response = await self._client.get(
                f"{self._base_url}/{ip_address}", params=self._credentials()
            )
            response.raise_for_status()
            return _country_in(response.json())
        except Exception as error:
            # The error CLASS only. An httpx message renders the full URL, which
            # carries the token this deployment authenticates with.
            logger.warning("geolocation lookup failed: %s", type(error).__name__)
            return None

    def _credentials(self) -> dict[str, str]:
        return {"token": self._token} if self._token else {}

    async def aclose(self) -> None:
        await self._client.aclose()


def _country_in(body: object) -> str | None:
    if not isinstance(body, dict):
        return None
    country = body.get(_COUNTRY_KEY) or body.get(_FALLBACK_COUNTRY_KEY)
    if not isinstance(country, str) or not country.strip():
        return None
    # Upper-cased, so one provider's `ru` and another's `RU` are one value in
    # Story 15's grouping rather than two countries.
    return country.strip().upper()


def create_geolocation() -> HttpGeolocation | None:
    """The configured client, or `None` when this deployment has none.

    `None` rather than an exception: a missing geolocation configuration is one
    unset analytics column, not a reason the application cannot start (§3.1).
    The caller substitutes `NullGeolocation` and logs the state once at boot.
    """
    base_url = os.environ.get(GEOLOCATION_URL_ENV_VAR, "").strip()
    if not base_url:
        return None
    return HttpGeolocation(
        base_url=base_url,
        token=os.environ.get(GEOLOCATION_TOKEN_ENV_VAR, "").strip(),
        timeout_seconds=float(os.environ.get(GEOLOCATION_TIMEOUT_ENV_VAR, DEFAULT_TIMEOUT_SECONDS)),
    )
