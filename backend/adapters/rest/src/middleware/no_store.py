"""`Cache-Control: no-store` on every response the profile routes can produce.

Setting the header in the route body covers the 200 and nothing else: a 401 is
raised by the `get_current_owner_id` dependency BEFORE the body runs, and both it
and the catch-all 500 are rendered by exception handlers that build a fresh
`JSONResponse` -- whatever the route wrote is gone. The body carries the account's
email, so "only the success path is uncacheable" is the wrong half to protect.

Pure ASGI rather than `BaseHTTPMiddleware`: the header is stamped onto the
`http.response.start` message on its way out, so it applies to whatever produced
the response and costs no request/response buffering.

One gap this cannot close by itself: Starlette builds `ServerErrorMiddleware`
(which renders the `Exception` handler's 500) OUTSIDE the user middleware stack,
so a 500 never passes through here. `error_handling/exception_handlers.py` stamps
that one at the source, keyed on the same `PROFILE_PATHS` set exported below --
which is why the set lives here and is imported there, rather than being written
out twice.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from starlette.datastructures import MutableHeaders

NO_STORE = "no-store"

# Exact paths, not a prefix: `/api/v1/auth/me` is the whole surface, and a prefix
# match would silently adopt any future `/auth/me*` route into a policy nobody
# chose for it.
PROFILE_PATHS = frozenset({"/api/v1/auth/me"})


class NoStoreMiddleware:
    def __init__(self, app: Any, paths: frozenset[str] = PROFILE_PATHS) -> None:
        self._app = app
        self._paths = paths

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[[], Awaitable[Any]],
        send: Callable[[Any], Awaitable[None]],
    ) -> None:
        if scope.get("type") != "http" or scope.get("path") not in self._paths:
            await self._app(scope, receive, send)
            return

        async def send_with_no_store(message: Any) -> None:
            if message["type"] == "http.response.start":
                # Assignment, not append: an existing Cache-Control is replaced,
                # so a route (or a future middleware) that set something weaker
                # cannot leave two contradictory directives for a proxy to pick
                # between.
                MutableHeaders(scope=message)["cache-control"] = NO_STORE
            await send(message)

        await self._app(scope, receive, send_with_no_store)
