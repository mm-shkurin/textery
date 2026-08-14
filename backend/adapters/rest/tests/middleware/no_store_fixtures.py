"""The app the `no_store` tests drive, and the paths they drive it on.

Its own module so the test file states claims and nothing else: every status in
that file is reached through the mechanism that actually produces it in the real
app -- a raised domain exception, a dependency that refuses, an unhandled error --
which takes a small router to arrange and would otherwise bury the assertions.
"""

import pytest
from fastapi import Depends, FastAPI, Response
from httpx import ASGITransport, AsyncClient
from middleware.no_store import PROFILE_PREFIX, NoStoreMiddleware

from error_handling.exception_handlers import (
    not_found_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from shared.exceptions import NotFoundException, ValidationException

PROFILE_PATH = PROFILE_PREFIX
AVATAR_PATH = f"{PROFILE_PREFIX}/avatar"
DELETION_PATH = f"{PROFILE_PREFIX}/deletion"
OTHER_PATH = "/api/v1/documents"
# Shares the prefix as a string but is not under it -- the guard against a
# `startswith` that would adopt `/api/v1/auth/members` into the profile policy.
NEIGHBOUR_PATH = f"{PROFILE_PREFIX}mbers"

DECLARED_DIRECTIVE = "private, no-cache"
UNRELATED_DIRECTIVE = "max-age=60"


def build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(NoStoreMiddleware)
    # Same suppression `main.py` carries, for the same reason: Starlette types the
    # handler as taking `Exception`, and the app registers handlers that take the
    # specific exception they are registered for. Loosening them to `Exception` to
    # satisfy the stub would erase a real guarantee.
    app.add_exception_handler(ValidationException, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(NotFoundException, not_found_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)

    def refuse_the_token() -> None:
        raise ValidationException(error_code="UNAUTHORIZED", message="no token")

    @app.get(PROFILE_PATH)
    async def profile() -> dict:
        return {"email": "ada@example.ru"}

    @app.patch(PROFILE_PATH)
    async def rename() -> dict:
        raise ValidationException(error_code="INVALID_NAME", message="bad name")

    @app.put(PROFILE_PATH)
    async def missing() -> dict:
        raise NotFoundException("nothing here")

    @app.post(PROFILE_PATH)
    async def broken() -> dict:
        raise RuntimeError("the driver blew up naming a table")

    @app.delete(PROFILE_PATH, dependencies=[Depends(refuse_the_token)])
    async def guarded() -> dict:
        return {}

    @app.head(PROFILE_PATH)
    async def cacheable(response: Response) -> dict:
        # A route that declares a directive of its own, the way `avatar_response`
        # declares `private, no-cache` -- the middleware must leave it alone.
        response.headers["cache-control"] = DECLARED_DIRECTIVE
        return {}

    @app.get(AVATAR_PATH)
    async def avatar() -> dict:
        raise NotFoundException("no avatar")

    @app.post(DELETION_PATH)
    async def deletion() -> dict:
        raise ValidationException(error_code="CONFIRMATION_INVALID", message="nope")

    @app.get(NEIGHBOUR_PATH)
    async def members() -> dict:
        return {}

    @app.get(OTHER_PATH)
    async def documents() -> dict:
        return {"items": []}

    @app.head(OTHER_PATH)
    async def cacheable_elsewhere(response: Response) -> dict:
        response.headers["cache-control"] = UNRELATED_DIRECTIVE
        return {}

    return app


@pytest.fixture
def client():
    return AsyncClient(
        transport=ASGITransport(app=build_app(), raise_app_exceptions=False),
        base_url="http://test",
    )
