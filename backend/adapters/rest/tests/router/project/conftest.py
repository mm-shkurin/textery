from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from error_handling.exception_handlers import validation_exception_handler
from project.project_item import ProjectItem
from router.project import project_router as project_router_module
from security.current_owner import get_current_owner_id, get_token_service
from shared.exceptions import InvalidTokenException, ValidationException

OWNER_ID = uuid4()


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
def feed_row():
    """Build a complete domain row carrying the given id.

    `ProjectItem` permits no field to be absent, so the eight fields this router
    test does not assert still have to be supplied. They are filled with values no
    assertion reads, and deliberately not with contract-plausible ones: what the
    serializer emits for them is pinned by the scenario that adds them to the
    envelope, not here.

    `kind` and `status` are the exception. projects_list.yaml declares them as
    enums, so `""` is not an implausible value but an *illegal* one -- a fixture
    that cannot occur in production would quietly outlive the day those fields
    grow constrained types. They carry the least interesting legal member
    instead; the free-form fields stay implausible.
    """

    def _make(project_id):
        return ProjectItem(
            kind="document",
            id=project_id,
            title="",
            preview="",
            document_type="",
            status="ready",
            retryable=False,
            created_at=datetime(1970, 1, 1, tzinfo=UTC),
            updated_at=datetime(1970, 1, 1, tzinfo=UTC),
        )

    return _make


@pytest.fixture
def owner_id():
    """The account id the overridden Bearer dependency resolves to."""
    return OWNER_ID
