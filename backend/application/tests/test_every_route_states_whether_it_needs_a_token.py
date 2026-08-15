"""Every served route either requires a token or is named here as deliberately public.

Ownership is enforced by a `Depends(get_current_owner_id)` parameter on each
route that needs it, which means it is enforced by remembering to type it. Six
routers do remember today; nothing checks the seventh. A new route added without
that parameter serves another account's data on its first request, and no
existing test notices -- the router suites exercise the routes they were written
for, and a route nobody wrote a test for is exactly the one that would be missed.

The public list is spelled out rather than derived. Deriving "public" from the
routes themselves would make this vacuous: an unauthenticated route would prove
its own right to be unauthenticated. Adding a route here is a deliberate line in
a diff that a reviewer sees, which is the whole mechanism.
"""

import pytest
from fastapi.routing import APIRoute

from security.current_owner import get_current_owner_id

# Routes that must answer without a token, and why each one has to.
_DELIBERATELY_PUBLIC = {
    # Account creation and the credential exchanges. A token cannot be required
    # by the endpoints whose job is to issue one.
    ("POST", "/api/v1/auth/register"),
    ("POST", "/api/v1/auth/verify"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/refresh"),
    ("POST", "/api/v1/auth/resend-code"),
    # The OAuth legs. `start` and `callback` are browser redirects the provider
    # drives, and `exchange` trades the one-time handoff code for the first token
    # pair -- all three run before the caller has one.
    ("GET", "/api/v1/auth/oauth/{provider}/start"),
    ("GET", "/api/v1/auth/oauth/{provider}/callback"),
    ("POST", "/api/v1/auth/oauth/exchange"),
    # Probed by the container's HEALTHCHECK and by the orchestrator, neither of
    # which holds an account.
    ("GET", "/health"),
}


def _dependency_functions(route: APIRoute) -> set[object]:
    """Every dependency reachable from this route, not only its direct ones.

    Walked recursively because `get_current_owner_id` may be reached through
    another dependency rather than declared on the handler, and a check that only
    looked one level deep would report a properly-guarded route as unguarded.
    """
    found: set[object] = set()
    pending = list(route.dependant.dependencies)
    while pending:
        dependency = pending.pop()
        if dependency.call is not None:
            found.add(dependency.call)
        pending.extend(dependency.dependencies)
    return found


def _api_routes(app) -> list[APIRoute]:
    """Every `APIRoute` the app serves, reached through whatever `app.routes` holds.

    It does not hold them directly. This FastAPI version defers each
    `include_router` behind an `_IncludedRouter` that carries no path of its own,
    so a plain `isinstance` filter over `app.routes` returns nothing -- which the
    third test below caught on the first run, and which is the same shape
    `test_composition_root_boots` sidesteps by reading the OpenAPI schema instead.

    The schema is no use here: it describes paths and verbs, not the dependency
    tree, and the dependency tree is the whole question. So this descends into
    `original_router` where it exists, tolerating both layouts rather than
    pinning the private attribute as the only one. If a future version renames it
    again, the guard test fails loudly instead of this file quietly inspecting an
    empty list.
    """
    found: list[APIRoute] = []
    pending = list(app.routes)
    seen: set[int] = set()
    while pending:
        route = pending.pop()
        if id(route) in seen:
            continue
        seen.add(id(route))
        if isinstance(route, APIRoute):
            found.append(route)
            continue
        nested = getattr(route, "original_router", None)
        if nested is not None:
            pending.extend(nested.routes)
        elif hasattr(route, "routes"):
            pending.extend(route.routes)
    return found


def _identify(route: APIRoute) -> list[tuple[str, str]]:
    # `methods` is typed optional on the Starlette base even though APIRoute always
    # sets it; the default keeps that from being a crash if it ever is None.
    methods = route.methods or set()
    return [(verb, route.path) for verb in sorted(methods) if verb not in {"HEAD", "OPTIONS"}]


class TestOwnershipIsEnforcedByTheRouterAndNotByMemory:
    def test_should_require_a_token_on_every_route_not_declared_public(self, app):
        unguarded = sorted(
            identity
            for route in _api_routes(app)
            for identity in _identify(route)
            if identity not in _DELIBERATELY_PUBLIC
            and get_current_owner_id not in _dependency_functions(route)
        )

        assert unguarded == [], (
            f"{unguarded} serve without `Depends(get_current_owner_id)` and are not "
            f"listed as deliberately public. A route missing that parameter answers "
            f"with another account's data on its first request. Add the dependency, "
            f"or add the route to _DELIBERATELY_PUBLIC with the reason it needs none."
        )

    def test_should_not_carry_a_public_entry_for_a_route_that_is_gone(self, app):
        """A stale exemption is worse than none: it pre-approves a future path.

        `/api/v1/auth/login` deleted and later re-added for something else would
        arrive already exempt, and the diff that re-added it would show no line
        about authentication at all.
        """
        served = {identity for route in _api_routes(app) for identity in _identify(route)}
        stale = sorted(_DELIBERATELY_PUBLIC - served)

        assert stale == [], f"{stale} are exempted here but no longer served"

    def test_should_find_the_routes_it_is_checking(self, app):
        """Guard the guard: an empty route list satisfies both checks above vacuously.

        `app.routes` is the thing at risk here -- `test_composition_root_boots`
        records that FastAPI has hidden included routers behind objects carrying
        no path before, in which case this would inspect nothing and pass.
        """
        guarded = [
            route
            for route in _api_routes(app)
            if get_current_owner_id in _dependency_functions(route)
        ]

        assert len(guarded) >= 8, (
            f"expected the token-guarded routes to be visible through `app.routes`; "
            f"found {len(guarded)}, which means this file is inspecting almost "
            f"nothing rather than that the routes stopped being guarded"
        )


@pytest.fixture(scope="module")
def app():
    from main import app as fastapi_app

    return fastapi_app
