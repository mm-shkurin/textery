"""The envelope every analytics write shares: its own session, and no exception out.

Four adapters in this package repeated the same eleven lines -- open a session
from the factory, do one statement, log a warning naming the failure's type, close
the session in a `finally`. Repeated, it was four chances to forget the `close`
or to let one adapter's failure become a raise; named once, it is the fail-open
rule itself rather than an idiom that happens to be copied correctly.

**Its own session, not the request's.** The caller is mid-registration or
mid-generation. A failed analytics INSERT on the request's session poisons the
transaction the product is in the middle of, which turns a missing marketing row
into a failed sign-up -- exactly the coupling Story 14's governing decision
forbids.

**The failure is logged by TYPE, never by message.** A driver error can carry the
statement and its parameters, and these rows hold visitor identifiers; the type
is what an operator needs to tell a timeout from a constraint.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# What "the database did not cooperate" actually looks like: a driver or mapper
# failure, a socket that went away, a deadline that passed. Deliberately NOT bare
# `Exception` -- an AttributeError or a TypeError here is a bug in this package,
# and swallowing it would leave analytics quietly writing nothing while every log
# line says the database is at fault.
INFRASTRUCTURE_FAILURES = (SQLAlchemyError, OSError, asyncio.TimeoutError)


async def in_own_session[T](
    session_factory: Callable[[], AsyncSession],
    what: str,
    work: Callable[[AsyncSession], Awaitable[T]],
    fallback: T,
) -> T:
    """Run `work` on a session of its own; answer `fallback` if the database fails."""
    session = session_factory()
    try:
        return await work(session)
    except INFRASTRUCTURE_FAILURES as error:
        logger.warning("%s: %s", what, type(error).__name__)
        return fallback
    finally:
        await session.close()
