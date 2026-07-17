from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from error_handling.exception_handlers import (
    not_found_exception_handler,
    validation_exception_handler,
)
from router.generation import generation_router as generation_router_module
from security.current_owner import get_current_owner_id, get_token_service
from shared.exceptions import InvalidTokenException, NotFoundException, ValidationException

OWNER_ID = uuid4()


@pytest.fixture
def owner_id():
    """The account id the overridden Bearer dependency resolves to.

    Exposed as a fixture rather than imported by tests: several conftest.py files
    sit on this suite's import path, so `from conftest import OWNER_ID` resolves to
    whichever one landed there first -- silently binding a different constant than
    the fixture uses, and turning owner assertions into confusing false failures.
    """
    return OWNER_ID


@pytest.fixture
def generation_app():
    app = FastAPI()
    app.include_router(generation_router_module.router)
    app.add_exception_handler(ValidationException, validation_exception_handler)
    # Registered because the router raises NotFoundException for an unknown id.
    # Without it the exception escapes to Starlette and the 404 test sees a 500 --
    # the app under test has to carry the same handler set the real one does, or
    # the test is asserting against an app that does not exist.
    app.add_exception_handler(NotFoundException, not_found_exception_handler)
    # A stand-in token service is always wired, even for the "no token" tests.
    # FastAPI resolves Depends(get_token_service) BEFORE running
    # get_current_owner_id, so leaving the composition-root stub in place makes
    # every unauthenticated request die on its NotImplementedError instead of
    # reaching the header check. get_current_owner_id itself stays real -- and it
    # never touches the service when the header is missing or malformed, so those
    # tests still exercise the real path.
    app.dependency_overrides[get_token_service] = lambda: _RejectingTokenService()
    return app


class _RejectingTokenService:
    """Rejects every token. Tests that need a token to be accepted override the
    owner dependency instead; tests that need a specific rejection re-override this.
    """

    def read_access_subject(self, access_token):
        raise InvalidTokenException("token rejected by the test double")


def _client_factory(app, provider_names, override_owner=True):
    """Wire mock usecases in as overrides for each name in `provider_names`.

    Providers are resolved at CALL time, not import time: this is a conftest, so an
    import-time lookup of a provider the router does not export yet aborts
    collection for every test in the directory rather than failing the one that
    needs it.

    `override_owner` defaults to True because most tests are about the endpoint's
    behaviour, not its auth. The 401 tests pass False so the real dependency runs.
    """

    def _make(*mock_usecases):
        for provider_name, mock_usecase in zip(provider_names, mock_usecases):
            provider = getattr(generation_router_module, provider_name)
            app.dependency_overrides[provider] = _returning(mock_usecase)
        if override_owner:
            app.dependency_overrides[get_current_owner_id] = lambda: OWNER_ID
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    return _make


def _returning(mock_usecase):
    """Build a zero-argument override that hands back `mock_usecase`.

    A closure, NOT `lambda mock=mock_usecase: mock`. FastAPI inspects an override's
    signature: a parameter with a default becomes a *query parameter*, so the
    late-binding trick makes FastAPI resolve `mock` from the request and pass its own
    value instead of the mock. The endpoint still answers 201 -- so the test looks
    like it passed -- while the mock the test holds records nothing.
    """
    return lambda: mock_usecase


_POST_PROVIDERS = ("get_request_generation_usecase", "get_generate_document_usecase")
_GET_PROVIDERS = ("get_get_generation_usecase",)
_LIST_PROVIDERS = ("get_list_generations_usecase",)


@pytest.fixture
def create_client(generation_app):
    return _client_factory(generation_app, _POST_PROVIDERS)


@pytest.fixture
def get_client(generation_app):
    return _client_factory(generation_app, _GET_PROVIDERS)


@pytest.fixture
def list_client(generation_app):
    return _client_factory(generation_app, _LIST_PROVIDERS)


@pytest.fixture
def unauthenticated_list_client(generation_app):
    """No owner override — the real Bearer dependency runs."""
    return _client_factory(generation_app, _LIST_PROVIDERS, override_owner=False)


@pytest.fixture
def unauthenticated_create_client(generation_app):
    """No owner override — the real Bearer dependency runs."""
    return _client_factory(generation_app, _POST_PROVIDERS, override_owner=False)


@pytest.fixture
def unauthenticated_get_client(generation_app):
    """No owner override — the real Bearer dependency runs."""
    return _client_factory(generation_app, _GET_PROVIDERS, override_owner=False)
