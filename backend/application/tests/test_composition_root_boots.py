"""The composition root must IMPORT and expose every route it claims to serve.

Written after a wiring gap shipped that 644 green tests could not see: a new
usecase factory was added to `document_wiring` and referenced from `main.py`, but
never re-exported from the `container` package's `__init__`. Every unit and
adapter suite still passed — they import the modules directly — while the
application itself died on startup with

    ImportError: cannot import name 'create_create_document_from_generation'
                 from 'container'

The gap is structural, not a one-off slip: nothing else in the suite imports
`app.main`, so the one file that has to agree with all the others was the one
file nothing checked. These tests are cheap (an import and a route inventory) and
they fail on exactly the class of mistake that is otherwise found by a human
watching a container refuse to boot.
"""

import pytest


@pytest.fixture(scope="module")
def app():
    # The import IS the first assertion: a missing re-export, a typo in a factory
    # name, or a circular import between wiring modules raises right here.
    from main import app as fastapi_app

    return fastapi_app


# Every path the frontend calls. Spelled out rather than derived from the routers,
# because deriving them from the same objects under test would make the check
# vacuous — the point is to state, independently, what the product needs to exist.
EXPECTED_ROUTES = [
    ("POST", "/api/v1/auth/register"),
    ("POST", "/api/v1/auth/verify"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/refresh"),
    ("POST", "/api/v1/auth/resend-code"),
    ("GET", "/api/v1/auth/oauth/{provider}/start"),
    ("GET", "/api/v1/auth/oauth/{provider}/callback"),
    ("POST", "/api/v1/auth/oauth/exchange"),
    ("POST", "/api/v1/generations"),
    ("GET", "/api/v1/generations"),
    ("GET", "/api/v1/generations/{generation_id}"),
    ("POST", "/api/v1/documents"),
    ("GET", "/api/v1/documents"),
    ("GET", "/api/v1/documents/{document_id}"),
    ("PUT", "/api/v1/documents/{document_id}"),
    ("GET", "/api/v1/documents/{document_id}/export"),
    # The conversion the auto path cannot work without: no route here means a
    # generated document has no id, so it can be neither saved nor exported.
    ("POST", "/api/v1/documents/from-generation"),
]


class TestTheApplicationBoots:
    def test_should_import_the_composition_root(self, app):
        assert app is not None

    @pytest.mark.parametrize(("method", "path"), EXPECTED_ROUTES)
    def test_should_serve_every_route_the_product_depends_on(self, app, method, path):
        served = {
            (verb, route["path"] if isinstance(route, dict) else route)
            for route, verbs in _routes(app).items()
            for verb in verbs
        }

        assert (method, path) in served, f"{method} {path} is not served"

    def test_should_wire_a_usecase_for_every_dependency_placeholder(self, app):
        """Each router declares `get_*_usecase` stubs that raise NotImplementedError.

        A stub with no override in `dependency_overrides` is a route that 500s on
        its first real request — wired enough to appear in the inventory above and
        not wired enough to answer. Asserting the count is non-zero would pass on
        a single override, so this asserts that no *declared* stub is missing.
        """
        from router.document.document_router import (
            get_create_document_from_generation_usecase,
        )

        assert get_create_document_from_generation_usecase in app.dependency_overrides


def _routes(app) -> dict[str, set[str]]:
    """Path -> HTTP verbs, read from the OpenAPI schema.

    The schema rather than `app.routes`: FastAPI defers included routers behind
    `_IncludedRouter` objects that carry no `path`, so walking `app.routes`
    reports only the four docs endpoints and would make this whole file vacuous.
    """
    return {path: {verb.upper() for verb in operations} for path, operations in app.openapi()["paths"].items()}
