"""What the server observes about the caller of an HTTP request.

The address is the interesting one. `request.client.host` behind a reverse proxy
is the proxy, so every account would register from the load balancer's address
and every rate-limit bucket would be one bucket
(`02_Integration_Tests.md` §1.5). `X-Forwarded-For` is caller-controllable in its
left-hand entries -- anyone can send a header claiming any address -- so the
only entry that means anything is the one the LAST trusted hop appended.

`TRUSTED_PROXY_HOPS` is therefore a deployment fact and not a guess: it is how
many proxies of ours sit in front of the application, and the address taken is
that many entries from the RIGHT. Set it too high and a caller can spoof their
address by padding the header; too low and the address stored is our own proxy's.
Infra §2.5 asserts the configured number against the deployment's actual chain.
"""

import os
from uuid import UUID

from fastapi import Request

TRUSTED_PROXY_HOPS_ENV_VAR = "TRUSTED_PROXY_HOPS"
# One: the repo's compose files put a single nginx in front of the application.
DEFAULT_TRUSTED_PROXY_HOPS = 1

FORWARDED_FOR = "X-Forwarded-For"
# The header is caller-controlled, so the parse is bounded before it is split.
MAX_FORWARDED_FOR_LENGTH = 1024


def trusted_proxy_hops() -> int:
    try:
        return max(0, int(os.environ.get(TRUSTED_PROXY_HOPS_ENV_VAR, DEFAULT_TRUSTED_PROXY_HOPS)))
    except ValueError:
        # A misconfigured value falls back to the documented default rather than
        # failing the boot: this decides one analytics column and one rate-limit
        # bucket, and neither is worth refusing to start over.
        return DEFAULT_TRUSTED_PROXY_HOPS


def client_ip_of(request: Request) -> str | None:
    """The caller's address as the last trusted hop reported it."""
    forwarded = request.headers.get(FORWARDED_FOR)
    if forwarded and len(forwarded) <= MAX_FORWARDED_FOR_LENGTH:
        candidate = _hop_from_the_right(forwarded, trusted_proxy_hops())
        if candidate:
            return candidate
    return request.client.host if request.client else None


def _hop_from_the_right(forwarded: str, hops: int) -> str | None:
    """The entry appended by the outermost trusted proxy.

    Counted from the right because that end is ours: each proxy APPENDS the
    address it saw, so the rightmost entries were written by infrastructure we
    control and the leftmost by whoever sent the request.
    """
    entries = [entry.strip() for entry in forwarded.split(",") if entry.strip()]
    if not entries:
        return None
    index = len(entries) - hops
    if index < 0:
        # The chain is shorter than configured -- a direct call that skipped a
        # proxy, or a request that arrived through fewer hops than usual. The
        # leftmost entry is the least-trusted one available; taking a spoofable
        # value here beats attributing the call to our own proxy.
        index = 0
    return entries[index]


def user_agent_of(request: Request) -> str | None:
    return request.headers.get("User-Agent")


def accept_language_of(request: Request) -> str | None:
    return request.headers.get("Accept-Language")


VISITOR_ID_HEADER = "X-Visitor-Id"


def visitor_id_of(request: Request) -> UUID | None:
    """The browser's own identity, when it sent one.

    A HEADER rather than a body field, so the product's request contracts are
    untouched: `POST /generations` accepts exactly the body it accepted before
    Story 14, and a client that sends nothing gets exactly the behaviour it had.

    Unparseable is `None`, never a refusal. This value decides one analytics
    join; no security, billing or entitlement decision may key on it (the
    published contract says so in as many words), so a malformed one costs a
    row in a funnel and must never cost a user their document.
    """
    raw = request.headers.get(VISITOR_ID_HEADER)
    if not raw:
        return None
    try:
        return UUID(raw)
    except ValueError:
        return None
