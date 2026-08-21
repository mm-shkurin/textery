"""Writing the ten registration-context columns onto an account row.

A targeted UPDATE of exactly the columns named, on its OWN session, swallowing
its own failures -- the three properties that keep this off the registration's
critical path:

* **Targeted**, not `save(account)`: the save path carries email, password_hash
  and is_verified from an entity read earlier in the request, so writing
  attribution through it would let a marketing parameter reinstate a stale
  password hash over a concurrent change.
* **Its own session**, so a failed UPDATE poisons no transaction the product is
  in the middle of.
* **Fail-open**, because a registration that succeeded must stay succeeded. The
  account exists and the user can sign in; what is lost is one row of marketing
  metadata, and one log line says so.
"""

import logging
from collections.abc import Callable
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from model.auth.account_model import AccountModel

logger = logging.getLogger(__name__)

# The only columns this writer is allowed to touch. An allowlist rather than
# "whatever the caller passed": the values arrive from request headers and query
# parameters, and a caller that could name the column would be able to write
# `is_verified` from a marketing link.
WRITABLE_COLUMNS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_content",
        "utm_term",
        "registration_ip",
        "registration_country",
        "device_type",
        "operating_system",
        "device_language",
    }
)


class SqlAlchemyRegistrationContextWriter:
    """`RegistrationContextWriter` over Postgres. Never raises."""

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._session_factory = session_factory

    async def record(self, account_id: UUID, values: dict[str, str | None]) -> None:
        writable = {name: value for name, value in values.items() if name in WRITABLE_COLUMNS}
        if not writable:
            return
        session = self._session_factory()
        try:
            await session.execute(
                update(AccountModel).where(AccountModel.id == account_id).values(**writable)
            )
            await session.commit()
        except Exception as error:
            logger.warning(
                "registration context was not stored for one account: %s", type(error).__name__
            )
        finally:
            await session.close()
