import logging

from shared.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


async def rollback_quietly(unit_of_work: UnitOfWork) -> None:
    """Roll back, and never let the rollback's own failure mask the real error.

    Every caller is already on a failure path and is about to raise the exception
    that actually explains what went wrong. If the rollback raises too, that
    second exception would replace the first and the response would describe the
    cleanup rather than the cause -- so it is caught here.

    Caught, but no longer silent. RegisterUser and VerifyAccount each carried an
    identical copy of this with a bare `except Exception: pass`, which is the
    part worth changing: a failed rollback leaves the session poisoned, the next
    query on it raises PendingRollbackError somewhere unrelated, and nothing in
    the logs connects that back to here. Logging it costs nothing on the happy
    path -- this function only runs when something has already gone wrong.
    """
    try:
        await unit_of_work.rollback()
    except Exception:
        logger.warning("rollback failed; the session may be left in a poisoned state", exc_info=True)
