"""`Cache-Control: no-store` on EVERY response the profile path can produce.

"Every" is the claim, and a test that only checks the 200 proves the weakest half
of it: the response that carries the account's email is also the one produced by
handlers that never run the route body. Each status below is reached through the
mechanism that actually produces it in the app -- a raised domain exception, a
dependency that refuses, an unhandled error -- rather than by returning a
hand-built response with that number on it.
"""

import pytest
from fastapi import Depends, FastAPI, Response
from httpx import ASGITransport, AsyncClient
from middleware.no_store import NO_STORE, PROFILE_PATHS, NoStoreMiddleware

from error_handling.exception_handlers import (
    not_found_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from shared.exceptions import NotFoundException, ValidationException

PROFILE_PATH = next(iter(PROFILE_PATHS))
OTHER_PATH = "/api/v1/documents"


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(NoStoreMiddleware)
    app.add_exception_handler(ValidationException, validation_exception_handler)
    app.add_exception_handler(NotFoundException, not_found_exception_handler)
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
        # A route that sets a weaker directive of its own, so the middleware has
        # something to overwrite rather than merely something to add.
        response.headers["cache-control"] = "max-age=60"
        return {}

    @app.get(OTHER_PATH)
    async def documents() -> dict:
        return {"items": []}

    @app.head(OTHER_PATH)
    async def cacheable_elsewhere(response: Response) -> dict:
        response.headers["cache-control"] = "max-age=60"
        return {}

    @app.get(PROFILE_PATH + "/avatar")
    async def avatar() -> dict:
        return {}

    return app


@pytest.fixture
def client():
    return AsyncClient(
        transport=ASGITransport(app=_build_app(), raise_app_exceptions=False),
        base_url="http://test",
    )


class TestTheHeaderIsOnEveryStatus:
    @pytest.mark.parametrize(
        ("method", "expected_status"),
        [("get", 200), ("patch", 400), ("put", 404), ("delete", 401), ("post", 500)],
    )
    async def test_stamps_no_store_on_the_profile_path(
        self, client, method: str, expected_status: int
    ):
        async with client:
            response = await getattr(client, method)(PROFILE_PATH)

        assert response.status_code == expected_status
        assert response.headers["cache-control"] == NO_STORE

    async def test_stamps_the_refusal_a_dependency_raised_before_the_body_ran(self, client):
        # The 401 is raised by the auth dependency, so nothing the route body could
        # set would ever be on this response.
        async with client:
            response = await client.delete(PROFILE_PATH)

        assert response.headers["cache-control"] == NO_STORE

    async def test_stamps_the_five_hundred_that_never_passes_through_the_middleware(self, client):
        # Starlette renders this one outside the user middleware stack; the header
        # is put on at the source instead. Without it the "every response" claim
        # would hold for four statuses and quietly miss the fifth.
        async with client:
            response = await client.post(PROFILE_PATH)

        assert response.status_code == 500
        assert response.headers["cache-control"] == NO_STORE

    async def test_does_not_leak_the_internal_error_into_the_body_it_stamps(self, client):
        async with client:
            response = await client.post(PROFILE_PATH)

        assert "driver blew up" not in response.text


class TestTheHeaderIsOnlyOnTheProfilePaths:
    async def test_leaves_an_unrelated_route_alone(self, client):
        async with client:
            response = await client.get(OTHER_PATH)

        assert "cache-control" not in response.headers

    async def test_matches_the_path_exactly_rather_than_by_prefix(self, client):
        # A prefix match would adopt any future `/auth/me*` route into a policy
        # nobody chose for it.
        async with client:
            response = await client.get(PROFILE_PATH + "/avatar")

        assert "cache-control" not in response.headers


class TestTheHeaderIsAssignedNotAppended:
    async def test_replaces_a_weaker_directive_the_route_already_set(self, client):
        # Two contradictory directives would leave a proxy to pick between them.
        async with client:
            response = await client.head(PROFILE_PATH)

        assert response.headers.get_list("cache-control") == [NO_STORE]

    async def test_the_same_route_shape_off_the_profile_path_keeps_its_own_directive(self, client):
        """The control for the test above: it proves the route really sets one.

        Without this, "the profile response says no-store" would pass just as
        happily against a route that never set a directive at all.
        """
        async with client:
            response = await client.head(OTHER_PATH)

        assert response.headers["cache-control"] == "max-age=60"


class TestNonHttpTraffic:
    async def test_passes_a_lifespan_scope_straight_through(self):
        # The middleware only knows how to stamp an HTTP response start message;
        # anything else must reach the app untouched rather than be inspected.
        seen: list[dict] = []

        async def app(scope, receive, send) -> None:  # noqa: ARG001 -- ASGI shape
            seen.append(scope)

        await NoStoreMiddleware(app)({"type": "lifespan"}, _no_receive, _no_send)

        assert seen == [{"type": "lifespan"}]


async def _no_receive() -> dict:
    return {"type": "lifespan.startup"}


async def _no_send(message: dict) -> None:
    raise AssertionError(f"nothing should have been sent, got {message!r}")
