"""Run two contending sessions with a deadline, so a lock bug FAILS the suite.

Every race test here has two sessions reaching for the same row under
`SELECT ... FOR UPDATE`. The failure mode that matters most -- a lock nobody
releases -- makes a bare `asyncio.gather` wait forever: the suite hangs, CI burns
its job timeout, and the report says "cancelled" rather than naming the test.
A hang is the one regression a test cannot report on its own.

The deadline is per race, not per test, and generous: these are two round trips
to a local database, so ten seconds is roughly two orders of magnitude of slack
for a loaded runner. It is a liveness bound, not a performance assertion -- it
must never go red because a machine was busy.
"""

import asyncio
from collections.abc import Coroutine
from typing import Any

RACE_TIMEOUT_SECONDS = 10.0


async def race(*contenders: Coroutine[Any, Any, Any]) -> list[Any]:
    try:
        return list(await asyncio.wait_for(asyncio.gather(*contenders), RACE_TIMEOUT_SECONDS))
    except TimeoutError as expiry:
        raise AssertionError(
            f"the contending sessions did not both finish within {RACE_TIMEOUT_SECONDS}s. "
            "A row lock that is taken and never released looks exactly like this; "
            "without the deadline the suite would hang here instead of failing."
        ) from expiry
