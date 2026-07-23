from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class OAuthRedirectDto:
    """A 302 leg of the handshake, captured WITHOUT following the redirect.

    The location header is the asserted surface: invariant I4 is about what the
    browser is handed, so the test has to see the raw header rather than whatever
    the redirect target eventually answers.
    """

    status_code: int
    location: Optional[str]


@dataclass(frozen=True)
class OAuthExchangeResponseDto:
    status_code: int
    body: Optional[dict]
