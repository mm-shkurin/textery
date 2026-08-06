"""Shared harness for the request-scoped wiring tests.

Every `create_*` factory in the composition root is a `@request_scoped` async
generator: it opens one session from `container.runtime.session_factory`, yields
the assembled usecase, and closes the session on the way out. Pinning what a
factory wired therefore means driving that generator protocol by hand --
`__anext__()` to reach the yield, `aclose()` in a `finally` so the session is
released even when an assertion fails -- around a `patch` of a module-path string.

That protocol is not what any of these tests is about; the assertions after the
yield are. It lived verbatim in three test files, along with the
`"container.runtime.session_factory"` patch target, so a rename of that attribute
would have been three separate silent breakages. It lives here once instead.
"""

import contextlib
from collections.abc import AsyncIterator, Callable
from unittest.mock import AsyncMock, MagicMock, patch

SESSION_FACTORY_TARGET = "container.runtime.session_factory"


@contextlib.asynccontextmanager
async def wired_on_one_session(
    factory: Callable[[], AsyncIterator],
) -> AsyncIterator[tuple]:
    """Resolve `factory` against a sentinel session, yielding `(usecase, session)`.

    The session is a `MagicMock` rather than a real one because these tests assert
    object identity -- that every collaborator was handed the SAME session -- which
    a sentinel proves and a real session cannot. `close` is an `AsyncMock` so the
    factory's own teardown can await it.
    """
    sentinel_session = MagicMock()
    sentinel_session.close = AsyncMock()

    with patch(SESSION_FACTORY_TARGET, return_value=sentinel_session):
        generator = factory()
        try:
            yield (await generator.__anext__(), sentinel_session)
        finally:
            await generator.aclose()
