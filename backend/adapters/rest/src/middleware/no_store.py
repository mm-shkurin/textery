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
that one at the source, keyed on the same `is_profile_path` predicate exported
below -- which is why the rule lives here and is imported there, rather than being
written out twice.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from starlette.datastructures import MutableHeaders

from router import api_routes

NO_STORE = "no-store"

# The whole profile family, not the one path: `/api/v1/auth/me/avatar` and
# `/api/v1/auth/me/deletion` are the same account's surface, and an exact set left
# their 401/404/500 -- rendered by the handlers below, with whatever the route body
# set discarded -- freely storable. A future `/auth/me*` route inherits no-store by
# default, which is the safe direction for a route nobody has reviewed yet.
PROFILE_PREFIX = api_routes.PROFILE


def is_profile_path(path: str) -> bool:
    return path == PROFILE_PREFIX or path.startswith(f"{PROFILE_PREFIX}/")


class NoStoreMiddleware:
    def __init__(self, app: Any) -> None:
        self._app = app

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[[], Awaitable[Any]],
        send: Callable[[Any], Awaitable[None]],
    ) -> None:
        if scope.get("type") != "http" or not is_profile_path(str(scope.get("path", ""))):
            await self._app(scope, receive, send)
            return

        async def send_with_no_store(message: Any) -> None:
            if message["type"] == "http.response.start":
                # Default, not override: a route that declared its own
                # Cache-Control chose it deliberately -- `avatar_response` serves
                # `private, no-cache` so a client may revalidate an image instead
                # of re-downloading it every paint. Only responses that declared
                # nothing (every error rendered by a handler) get no-store, so the
                # two directives can never contradict each other on one response.
                headers = MutableHeaders(scope=message)
                if "cache-control" not in headers:
                    headers["cache-control"] = NO_STORE
            await send(message)

        await self._app(scope, receive, send_with_no_store)
