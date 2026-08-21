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

from dataclasses import dataclass
from uuid import UUID

from fastapi import Request

from analytics.transport_settings import max_forwarded_for_length, trusted_proxy_hops

FORWARDED_FOR = "X-Forwarded-For"


def client_ip_of(request: Request) -> str | None:
    """The caller's address as the last trusted hop reported it."""
    forwarded = request.headers.get(FORWARDED_FOR)
    if forwarded and len(forwarded) <= max_forwarded_for_length():
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


@dataclass(frozen=True)
class ObservedContext:
    """What the SERVER saw about the request, never what the body claimed.

    The three travel together everywhere an account can be born -- `/register`
    and the OAuth callback -- because an account created either way has to carry
    the same technical context. Read as one value so the two routes cannot come
    to read a different set, and so a fourth fact is added in one place.

    Never accepted from a request body: a client that could set its own country
    or device type could fabricate the segmentation the business is measured by,
    and nothing in the stored data would reveal it.
    """

    client_ip: str | None
    user_agent: str | None
    accept_language: str | None


def observed_context(request: Request) -> ObservedContext:
    return ObservedContext(
        client_ip=client_ip_of(request),
        user_agent=user_agent_of(request),
        accept_language=accept_language_of(request),
    )


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


# The five names a marketing link carries, in the order `endpoints.md` lists them.
UTM_PARAMETERS = ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term")


def campaign_parameters_of(request: Request) -> dict[str, str | None]:
    """The five `utm_*` as the query string carried them, unvalidated.

    Read off the query string rather than declared as route parameters, and that
    is the whole point on `/auth/oauth/{provider}/start`: a declared parameter
    with a type is a parameter FastAPI can REFUSE, and that route answers
    302/404/500 with no 400 at all. Whatever is here is decided by
    `Attribution.of` when it is stored, where an unusable member costs the
    marketing report and never the visitor.
    """
    return {name: request.query_params.get(name) for name in UTM_PARAMETERS}
