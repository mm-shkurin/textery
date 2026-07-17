import logging

from shared.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


async def rollback_quietly(unit_of_work: UnitOfWork) -> None:
    """Roll back, and never let the rollback's own failure mask the real error.

    Every caller is already on a failure path and is about to raise the exception
    that actually explains what went wrong. If the rollback raises too, that
    second exception would replace the first and the response would describe the
    cleanup rather than the cause -- so it is caught here.

    Caught, but not silent. A failed rollback leaves the session poisoned, the
    next query on it raises PendingRollbackError somewhere unrelated, and without
    this line nothing connects that back here. Logging costs nothing on the happy
    path: this runs only when something has already gone wrong.
    """
    try:
        await unit_of_work.rollback()
    except Exception:
        logger.warning(
            "rollback failed; the session may be left in a poisoned state", exc_info=True
        )
