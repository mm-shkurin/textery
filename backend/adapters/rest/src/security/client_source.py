"""The caller identity every per-source bound in this layer keys on.

One function, three callers -- the analytics ingest bound, the three OAuth legs
and the three password routes -- because a bucket subject computed two different
ways is two different subjects: the same caller would get two allowances, and
which one it spent would depend on which route it hit.
"""

import hashlib

from fastapi import Request

from analytics.client_context import client_ip_of


def hashed_client_source(request: Request) -> str:
    """The caller's address, one-way hashed.

    Hashed because these counters must not become a permanent visitor log
    (`03_Security_Tests.md` §5.2, §5.4): a bound needs to tell two callers apart,
    which a digest does, and never needs to know who either of them is. Truncated
    to 32 hex characters -- still far past any collision that matters for a
    per-window counter, and short enough to be a comfortable index key.

    The address comes from `client_ip_of`, so the hop actually trusted is the one
    `TRUSTED_PROXY_HOPS` names. Reading the header directly, as this layer did in
    two places, silently takes the rightmost entry whatever the deployment's chain
    length is -- and the rightmost entry behind two proxies is our own inner one,
    which puts every caller in the world into a single bucket.
    """
    client_ip = client_ip_of(request) or ""
    return hashlib.sha256(client_ip.encode("utf-8")).hexdigest()[:32]
