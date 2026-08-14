"""`Cache-Control: no-store` on EVERY response the profile path can produce.

"Every" is the claim, and a test that only checks the 200 proves the weakest half
of it: the response that carries the account's email is also the one produced by
handlers that never run the route body. Each status below is reached through the
mechanism that actually produces it in the app -- a raised domain exception, a
dependency that refuses, an unhandled error -- rather than by returning a
hand-built response with that number on it.
"""

import pytest
from middleware.no_store import NO_STORE, NoStoreMiddleware
from no_store_fixtures import (
    AVATAR_PATH,
    DECLARED_DIRECTIVE,
    DELETION_PATH,
    NEIGHBOUR_PATH,
    OTHER_PATH,
    PROFILE_PATH,
    UNRELATED_DIRECTIVE,
    client,
)

__all__ = ["client"]


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

    @pytest.mark.parametrize(
        ("method", "path", "expected_status"),
        [("get", AVATAR_PATH, 404), ("post", DELETION_PATH, 400)],
    )
    async def test_stamps_the_errors_of_the_routes_under_the_profile_path(
        self, client, method: str, path: str, expected_status: int
    ):
        # These two are the same account's surface, and their 4xx/5xx are rendered
        # by the handlers -- whatever the route body set is gone by then.
        async with client:
            response = await getattr(client, method)(path)

        assert response.status_code == expected_status
        assert response.headers["cache-control"] == NO_STORE

    async def test_leaves_a_route_that_merely_shares_the_prefix_string_alone(self, client):
        # `/api/v1/auth/members` starts with `/api/v1/auth/me` as text but is not
        # under it; a bare `startswith` would adopt it into a policy nobody chose.
        async with client:
            response = await client.get(NEIGHBOUR_PATH)

        assert "cache-control" not in response.headers


class TestTheHeaderIsADefaultNotAnOverride:
    async def test_keeps_the_directive_the_route_declared_for_itself(self, client):
        # `avatar_response` serves `private, no-cache` on purpose: the client may
        # revalidate the image instead of re-downloading it on every paint.
        # Exactly one directive either way -- two would leave a proxy to choose.
        async with client:
            response = await client.head(PROFILE_PATH)

        assert response.headers.get_list("cache-control") == [DECLARED_DIRECTIVE]

    async def test_the_same_route_shape_off_the_profile_path_keeps_its_own_directive(self, client):
        """The control for the test above: it proves the route really sets one.

        Without this, "the profile response kept its directive" would pass just as
        happily against a middleware that stamped nothing anywhere.
        """
        async with client:
            response = await client.head(OTHER_PATH)

        assert response.headers["cache-control"] == UNRELATED_DIRECTIVE


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
