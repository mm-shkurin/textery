"""Endpoint configuration for the OAuth adapters.

Same two layers as the generation provider: `oauth_endpoints.toml` ships with the
package so a clone works unconfigured, and an environment variable named beside
each key wins where a deployment sets one.
"""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

_ENDPOINTS_FILE = Path(__file__).with_name("oauth_endpoints.toml")


@dataclass(frozen=True)
class YandexEndpoints:
    authorize: str
    token: str
    info: str
    timeout_seconds: float


def _text(env_var: str, fallback: str) -> str:
    return os.environ.get(env_var) or fallback


def _seconds(env_var: str, fallback: float) -> float:
    """The override, or the shipped default when it is unset or not a number.

    A malformed override falls back rather than killing the boot: this bounds a
    sign-in call, and refusing to start over a mistyped timeout trades a slow
    login for no login at all.
    """
    raw = os.environ.get(env_var)
    if not raw:
        return fallback
    try:
        return float(raw)
    except ValueError:
        return fallback


def load_yandex_endpoints() -> YandexEndpoints:
    with _ENDPOINTS_FILE.open("rb") as handle:
        configured = tomllib.load(handle)["yandex"]
    return YandexEndpoints(
        authorize=_text("YANDEX_AUTHORIZE_URL", configured["authorize"]),
        token=_text("YANDEX_TOKEN_URL", configured["token"]),
        info=_text("YANDEX_INFO_URL", configured["info"]),
        timeout_seconds=_seconds("YANDEX_TIMEOUT_SECONDS", configured["timeout_seconds"]),
    )


YANDEX = load_yandex_endpoints()
