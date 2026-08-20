"""Where the GigaChat adapter's endpoints, timeouts and trust bundle come from.

They used to be module constants in `gigachat_provider.py`. Two problems with
that, and only one of them is cosmetic: an endpoint move or a longer read budget
became a source edit that has to clear lint, types and a test run before it can
ship, and a reviewer reading the adapter could not tell which values a deployment
is allowed to change from those that are part of the protocol.

Two layers, in this order:

1. `gigachat_defaults.toml`, which travels with the package — a fresh clone works
   with nothing exported.
2. The environment, which wins. Every key names its variable in the TOML file
   itself, so the override list cannot drift from the values it overrides.
"""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_DEFAULTS_FILE = Path(__file__).with_name("gigachat_defaults.toml")


def _defaults() -> dict:
    with _DEFAULTS_FILE.open("rb") as handle:
        return tomllib.load(handle)


def _text(env_var: str, fallback: str) -> str:
    return os.environ.get(env_var) or fallback


def _seconds(env_var: str, fallback: float) -> float:
    raw = os.environ.get(env_var)
    return float(raw) if raw else float(fallback)


@dataclass(frozen=True)
class GigaChatSettings:
    token_url: str
    completions_url: str
    scope: str
    model: str
    ca_bundle: str
    connect_timeout: float
    read_timeout: float
    write_timeout: float
    pool_timeout: float
    token_read_timeout: float
    token_ttl: float
    token_expiry_margin: float


def _ca_bundle(configured: str) -> str:
    """An absolute path is taken as given; a relative one is package-relative.

    The bundle ships inside the adapter because GigaChat's chain chains to a CA
    no default trust store carries, so the shipped copy has to resolve from
    wherever the process happens to be started.
    """
    path = Path(configured)
    return str(path if path.is_absolute() else _PACKAGE_ROOT / path)


def load_settings() -> GigaChatSettings:
    config = _defaults()
    endpoints, tls, timeouts, cache = (
        config["endpoints"],
        config["tls"],
        config["timeouts"],
        config["token_cache"],
    )
    return GigaChatSettings(
        token_url=_text("GIGACHAT_TOKEN_URL", endpoints["token"]),
        completions_url=_text("GIGACHAT_COMPLETIONS_URL", endpoints["completions"]),
        scope=_text("GIGACHAT_SCOPE", endpoints["scope"]),
        model=_text("GIGACHAT_MODEL", endpoints["model"]),
        ca_bundle=_ca_bundle(_text("GIGACHAT_CA_BUNDLE", tls["ca_bundle"])),
        connect_timeout=_seconds("GIGACHAT_CONNECT_TIMEOUT_SECONDS", timeouts["connect"]),
        read_timeout=_seconds("GIGACHAT_READ_TIMEOUT_SECONDS", timeouts["read"]),
        write_timeout=_seconds("GIGACHAT_WRITE_TIMEOUT_SECONDS", timeouts["write"]),
        pool_timeout=_seconds("GIGACHAT_POOL_TIMEOUT_SECONDS", timeouts["pool"]),
        token_read_timeout=_seconds("GIGACHAT_TOKEN_READ_TIMEOUT_SECONDS", timeouts["token_read"]),
        token_ttl=_seconds("GIGACHAT_TOKEN_TTL_SECONDS", cache["ttl"]),
        token_expiry_margin=_seconds(
            "GIGACHAT_TOKEN_EXPIRY_MARGIN_SECONDS", cache["expiry_margin"]
        ),
    )


SETTINGS = load_settings()
