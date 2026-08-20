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


def _text(env_var: str, fallback: str) -> str:
    return os.environ.get(env_var) or fallback


def load_yandex_endpoints() -> YandexEndpoints:
    with _ENDPOINTS_FILE.open("rb") as handle:
        configured = tomllib.load(handle)["yandex"]
    return YandexEndpoints(
        authorize=_text("YANDEX_AUTHORIZE_URL", configured["authorize"]),
        token=_text("YANDEX_TOKEN_URL", configured["token"]),
        info=_text("YANDEX_INFO_URL", configured["info"]),
    )


YANDEX = load_yandex_endpoints()
