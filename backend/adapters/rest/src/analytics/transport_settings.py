"""Where the ingest route's and the proxy parse's bounds come from.

They were module constants beside the code that read them, which made every one
of them a source edit: a longer proxy chain or a tighter rate limit could not be
deployed without a build. Two layers, in this order:

1. `transport_defaults.toml`, which travels with the package, so a fresh clone
   runs with nothing exported.
2. The environment, which wins. Every key names its variable in the TOML itself,
   so the override list cannot drift from the values it overrides.

A malformed environment value falls back to the shipped default and says so in
the log rather than refusing to start: these bound abuse, and a typo in one of
them must not be able to take the process down.
"""

import logging
import os
import tomllib
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULTS_FILE = Path(__file__).with_name("transport_defaults.toml")

with _DEFAULTS_FILE.open("rb") as _handle:
    _DEFAULTS = tomllib.load(_handle)

_INGEST = _DEFAULTS["ingest"]
_PROXY = _DEFAULTS["proxy"]

MAX_BODY_BYTES_ENV_VAR = "ANALYTICS_MAX_BODY_BYTES"
EVENT_RATE_LIMIT_ENV_VAR = "ANALYTICS_EVENT_RATE_LIMIT"
EVENT_RATE_WINDOW_ENV_VAR = "ANALYTICS_EVENT_RATE_WINDOW_SECONDS"
TRUSTED_PROXY_HOPS_ENV_VAR = "TRUSTED_PROXY_HOPS"
MAX_FORWARDED_FOR_LENGTH_ENV_VAR = "MAX_FORWARDED_FOR_LENGTH"


def _bounded_int(env_var: str, fallback: int, minimum: int) -> int:
    raw = os.environ.get(env_var)
    if raw is None:
        return int(fallback)
    try:
        value = int(raw)
    except ValueError:
        logger.warning("%s is not an integer (%r); using %s", env_var, raw, fallback)
        return int(fallback)
    if value < minimum:
        logger.warning("%s is below %s (%s); using %s", env_var, minimum, value, fallback)
        return int(fallback)
    return value


def max_body_bytes() -> int:
    return _bounded_int(MAX_BODY_BYTES_ENV_VAR, _INGEST["max_body_bytes"], minimum=1)


def event_rate_limit() -> int:
    return _bounded_int(EVENT_RATE_LIMIT_ENV_VAR, _INGEST["event_rate_limit"], minimum=1)


def event_rate_window_seconds() -> int:
    return _bounded_int(EVENT_RATE_WINDOW_ENV_VAR, _INGEST["event_rate_window_seconds"], minimum=1)


def trusted_proxy_hops() -> int:
    return _bounded_int(TRUSTED_PROXY_HOPS_ENV_VAR, _PROXY["trusted_hops"], minimum=0)


def max_forwarded_for_length() -> int:
    return _bounded_int(
        MAX_FORWARDED_FOR_LENGTH_ENV_VAR, _PROXY["max_forwarded_for_length"], minimum=1
    )
