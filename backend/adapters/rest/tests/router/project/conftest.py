from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

# Imported for their side effect: pytest registers a fixture whose function object
# is in the conftest namespace. The three row builders moved out because this file
# had grown past the 200-line limit, and they are the part that grows with the
# contract rather than with the router.
from row_builders import (  # noqa: F401
    contract_row,
    expected_row,
    feed_row,
)

from error_handling.exception_handlers import validation_exception_handler
from project.project_page import ProjectPage
from router.project import project_router as project_router_module
from security.current_owner import get_account_existence, get_current_owner_id, get_token_service
from shared.exceptions import InvalidTokenException, ValidationException

OWNER_ID = uuid4()


class _EveryAccountExists:
    """The `AccountExistence` port for tests that are not about a deleted account.

    Wired everywhere `get_token_service` is, because `get_current_owner_id`
    resolves both: without it every auth test dies on the composition root's
    NotImplementedError instead of reaching the header check it is asserting.
    Says yes unconditionally — a test that needs the "account is gone" branch
    overrides this with its own double rather than parameterising this one.
    """

    async def exists(self, account_id) -> bool:  # noqa: ARG002
        return True


@pytest.fixture
def project_app():
    app = FastAPI()
    app.include_router(project_router_module.router)
    app.add_exception_handler(ValidationException, validation_exception_handler)
    # A stand-in token service is always wired, even for the "no token" tests:
    # FastAPI resolves Depends(get_token_service) BEFORE running
    # get_current_owner_id, so leaving the composition-root stub in place would
    # make every unauthenticated request die on its NotImplementedError instead
    # of reaching the header check. get_current_owner_id itself stays real, and
    # it never touches the service when the header is missing.
    app.dependency_overrides[get_account_existence] = _EveryAccountExists
    app.dependency_overrides[get_token_service] = lambda: _RejectingTokenService()
    return app


class _RejectingTokenService:
    """Rejects every token. Tests that need a resolved owner override the owner
    dependency instead."""

    def read_access_subject(self, access_token):
        raise InvalidTokenException("token rejected by the test double")


def _client_factory(app, provider_name, override_owner=True):
    """Wire `mock_usecase` in as the override for `provider_name`.

    The provider is resolved at CALL time, not import time: this is a conftest, so
    an import-time lookup of a provider the router does not export yet would abort
    collection for every test in the directory rather than failing the one that
    needs it.
    """

    def _make(mock_usecase):
        provider = getattr(project_router_module, provider_name)
        app.dependency_overrides[provider] = lambda: mock_usecase
        if override_owner:
            app.dependency_overrides[get_current_owner_id] = lambda: OWNER_ID
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    return _make


@pytest.fixture
def feed_client(project_app):
    return _client_factory(project_app, "get_list_projects_usecase")


@pytest.fixture
def unauthenticated_feed_client(project_app):
    """No owner override -- the real Bearer dependency runs."""
    return _client_factory(project_app, "get_list_projects_usecase", override_owner=False)


@pytest.fixture
def feed_serving(mocker):
    """A usecase double whose `execute` serves the given rows as one page.

    The double is returned rather than wired into the client, because two tests
    read it back afterwards -- `assert_awaited_once_with` for the owner-scoping
    predicate, `assert_not_awaited` for the unauthenticated refusal.

    Only the *frame* is shared. The rows stay at each call site: what a scenario
    seeds is what it pins, and burying that under a wrapper is what this fixture
    exists to undo. The 401 test builds its own bare `AsyncMock` instead of using
    this -- handing it a `ProjectPage` would install a page it exists to prove is
    never fetched.
    """

    def _make(*rows, page=1, limit=20, total=None):
        # `total` defaults to the row count only because most callers do not care
        # about it. The row-serialization test passes it explicitly, so a rest
        # layer that derived the counter from `len(items)` instead of forwarding
        # the domain's still fails there.
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(
            return_value=ProjectPage(
                items=rows, page=page, limit=limit, total=len(rows) if total is None else total
            )
        )
        return usecase

    return _make


@pytest.fixture
def owner_id():
    """The account id the overridden Bearer dependency resolves to."""
    return OWNER_ID
