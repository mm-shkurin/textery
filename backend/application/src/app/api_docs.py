"""Whether this process publishes its own API documentation, and to whom.

`FastAPI()` serves `/docs`, `/redoc` and `/openapi.json` unconditionally unless
told otherwise, and this app never told it otherwise. That is invisible through
the frontend origin -- `infra/docker/nginx/frontend.conf` proxies only `/api/`,
so those three paths hit `try_files` and return the SPA -- but
`infra/docker-compose.yml` publishes the backend's own port on the host
(`${BACKEND_PORT}:8000`), and on that port they answer. Every route, every
request and response schema, every error code, published to anyone who reaches
the port.

The default is off, which is a behaviour change and a deliberate one. An
"expose unless disabled" switch is exposed in exactly the environments where
nobody thought about it, which are the ones that matter; an "enable to see it"
switch is off in those and takes one line in `.env` everywhere it is wanted.
Local development is where it is wanted, so `.env.example` turns it on.
"""

import os
from typing import NamedTuple

API_DOCS_ENABLED_ENV_VAR = "API_DOCS_ENABLED"

# Spelled out rather than "anything but empty is true": `API_DOCS_ENABLED=false`
# and `API_DOCS_ENABLED=0` are what someone writes when they mean off, and under
# a truthiness test both would turn it on -- the exact opposite of the intent,
# silently. Everything unrecognised is off, because this is the fail-closed side.
_TRUTHY = frozenset({"1", "true", "yes", "on"})


def api_docs_enabled() -> bool:
    return os.environ.get(API_DOCS_ENABLED_ENV_VAR, "").strip().lower() in _TRUTHY


class DocsUrls(NamedTuple):
    """The three `FastAPI()` arguments that decide this, answered together.

    One value carrying all three, rather than three call sites reading the same
    flag, because they have to agree: leaving `openapi_url` set while clearing
    `docs_url` hides the viewer and still publishes the schema it was rendering,
    which reads as "documentation disabled" while disabling nothing that matters.

    A NamedTuple and not a dict, so the call site can pass the fields by name.
    `FastAPI(**mapping)` type-checks against nothing useful -- mypy widens a
    heterogeneous mapping to `str | None` and matches it against every parameter
    of a very wide signature, reporting the mismatch against `debug: bool` and
    fourteen others.
    """

    docs_url: str | None
    redoc_url: str | None
    openapi_url: str | None


def docs_urls() -> DocsUrls:
    if api_docs_enabled():
        return DocsUrls(docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json")
    return DocsUrls(docs_url=None, redoc_url=None, openapi_url=None)
