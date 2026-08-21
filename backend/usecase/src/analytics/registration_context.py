"""The ports registration attribution needs, and their do-nothing defaults.

Two collaborators, both optional at construction and both fail-open at use:

* `RegistrationContextWriter` writes the ten columns onto an account row with a
  targeted UPDATE. Targeted, not `save(account)`: the save path carries email,
  password_hash and is_verified from an entity read earlier in the request, so
  writing attribution through it would let a marketing parameter reinstate a
  stale password hash. Attribution has no business touching either column.
* `Geolocation` turns the caller's address into a country. It is an outbound
  network dependency on the registration path, which is why the contract is
  "answer or `None`" rather than "answer or raise": an address that has no
  country and a lookup that could not be made both store NULL, and neither
  delays or fails a registration (`04_Infrastructure_Tests.md` §2.1-§2.3).
"""

import logging
from typing import Protocol
from uuid import UUID

logger = logging.getLogger(__name__)


class RegistrationContextWriter(Protocol):
    async def record(self, account_id: UUID, values: dict[str, str | None]) -> None:
        """Write the registration-context columns for one account. Never raises."""
        ...


class NullRegistrationContextWriter:
    async def record(self, account_id: UUID, values: dict[str, str | None]) -> None:
        logger.debug("registration context not wired; nothing stored")


class Geolocation(Protocol):
    async def country_of(self, ip_address: str | None) -> str | None:
        """The caller's country, or `None`. Never raises, never hangs."""
        ...


class NullGeolocation:
    """The default, and a legitimate production state.

    A deployment with no geolocation configuration boots and registers accounts
    with `registration_country` NULL (`04_Infrastructure_Tests.md` §3.1). Missing
    configuration is not a failed boot -- it is one analytics column unset.
    """

    async def country_of(self, ip_address: str | None) -> str | None:
        return None
