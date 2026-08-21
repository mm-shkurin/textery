"""Carrying a marketing link's campaign through the OAuth handshake.

The account is created inside `/callback`, two redirects away from anything a
client can put in a body -- so without this, EVERY account created through a
provider registers with NULL attribution. That is not a gap in a report, it is a
working sign-up channel missing from CAC-by-UTM entirely, and nothing in the data
would reveal the bias toward the email channel
(`endpoints.md`, "OAuth sign-up gets attribution too -- via `/start`").

So `/start` accepts the five parameters and parks them against the CSRF state it
already writes; `/callback` takes them back when it creates the account. They are
never forwarded to the provider.

Parked against the STATE VALUE, which is server-minted, single-use and already
the thing the callback proves it holds. A client cannot read another visitor's
parked campaign without already having their state, and having their state is the
attack the state exists to prevent.

Fail-open on both sides, like the rest of this story: `/start` is a redirect route
that answers 302/404/500 and has no 400 at all, and it does not get one here. A
broken marketing link must never end at a broken sign-in.
"""

import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class OAuthAttributionParking(Protocol):
    async def park(self, state_value: str, campaign_parameters: dict[str, str | None]) -> None:
        """Hold this handshake's campaign until the callback. Never raises."""
        ...

    async def take(self, state_value: str) -> dict[str, str | None]:
        """The campaign parked for this handshake, `{}` if none. Never raises."""
        ...


class NullOAuthAttributionParking:
    async def park(self, state_value: str, campaign_parameters: dict[str, str | None]) -> None:
        logger.debug("oauth attribution parking not wired; nothing parked")

    async def take(self, state_value: str) -> dict[str, str | None]:
        return {}
