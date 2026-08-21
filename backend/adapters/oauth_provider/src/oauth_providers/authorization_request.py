"""The authorization-request URL both providers build, written once.

The fake and the Yandex adapter deliberately produce byte-identical redirects --
that is what lets a stend run swap one for the other without routes, state
binding or the acceptance suite noticing. Two hand-copied `urlencode` blocks is
how they stop being identical: a parameter added to one is a divergence nothing
fails on until a real sign-in is attempted.
"""

from urllib.parse import urlencode


def authorization_url(authorize_url: str, client_id: str, redirect_uri: str, state: str) -> str:
    """`authorize_url` with the four query parameters an authorization request carries."""
    query = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
        }
    )
    return f"{authorize_url}?{query}"
