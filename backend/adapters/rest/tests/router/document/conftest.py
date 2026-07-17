from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from error_handling.exception_handlers import (
    conflict_exception_handler,
    not_found_exception_handler,
    validation_exception_handler,
)
from router.document import document_router as document_router_module
from security.current_owner import get_current_owner_id, get_token_service
from shared.exceptions import (
    ConflictException,
    InvalidTokenException,
    NotFoundException,
    ValidationException,
)

OWNER_ID = uuid4()


@pytest.fixture
def document_app():
    app = FastAPI()
    app.include_router(document_router_module.router)
    app.add_exception_handler(ValidationException, validation_exception_handler)
    app.add_exception_handler(NotFoundException, not_found_exception_handler)
    app.add_exception_handler(ConflictException, conflict_exception_handler)
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


def _client_factory(app, provider_name, override_owner=True):
    """Wire `mock_usecase` in as the override for `provider_name`.

    The provider is resolved at CALL time, not import time: this is a conftest, so
    an import-time lookup of a provider the router does not export yet aborts
    collection for every test in the directory rather than failing the one that
    needs it. Story 7's /verify work proved that empirically.

    `override_owner` defaults to True because most tests are about the endpoint's
    behaviour, not its auth. The 401 tests pass False so the real dependency runs.
    """

    def _make(mock_usecase):
        provider = getattr(document_router_module, provider_name)
        app.dependency_overrides[provider] = lambda: mock_usecase
        if override_owner:
            app.dependency_overrides[get_current_owner_id] = lambda: OWNER_ID
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    return _make


@pytest.fixture
def create_client(document_app):
    return _client_factory(document_app, "get_create_document_usecase")


@pytest.fixture
def get_client(document_app):
    return _client_factory(document_app, "get_get_document_usecase")


@pytest.fixture
def save_client(document_app):
    return _client_factory(document_app, "get_save_document_usecase")


@pytest.fixture
def list_client(document_app):
    return _client_factory(document_app, "get_list_documents_usecase")


@pytest.fixture
def unauthenticated_list_client(document_app):
    """No owner override — the real Bearer dependency runs."""
    return _client_factory(document_app, "get_list_documents_usecase", override_owner=False)


@pytest.fixture
def owner_id():
    """The account id the overridden Bearer dependency resolves to."""
    return OWNER_ID


@pytest.fixture
def unauthenticated_create_client(document_app):
    """No owner override — the real Bearer dependency runs."""
    return _client_factory(document_app, "get_create_document_usecase", override_owner=False)
