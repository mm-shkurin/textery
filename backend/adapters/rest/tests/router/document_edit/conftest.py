from uuid import uuid4

import pytest
from ai_edit_routes import ALL_ROUTES
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from document.resolve_owned_document import REFUSAL_MESSAGE
from error_handling.exception_handlers import (
    conflict_exception_handler,
    not_found_exception_handler,
    validation_exception_handler,
)
from router.document_edit import document_edit_router as router_module
from security.current_owner import get_current_owner_id, get_token_service
from shared.exceptions import (
    ConflictException,
    InvalidTokenException,
    NotFoundException,
    ValidationException,
)

OWNER_ID = uuid4()

# Distinguishes "the caller did not override the body" from "the caller asked for no
# body at all". `None` cannot serve as that default: it is itself a valid body value.
_ROUTE_DEFAULT = object()


@pytest.fixture
def owner_id():
    """The account id the overridden Bearer dependency resolves to.

    A fixture rather than an importable constant: several conftest.py files sit on
    this suite's import path, so `from conftest import OWNER_ID` resolves to
    whichever landed there first and silently binds a different value.
    """
    return OWNER_ID


@pytest.fixture
def ai_edit_app():
    app = FastAPI()
    app.include_router(router_module.router)
    app.add_exception_handler(ValidationException, validation_exception_handler)
    app.add_exception_handler(NotFoundException, not_found_exception_handler)
    # Registered deliberately, even though no test wants a 409: the ADR forbids the
    # queue route answering 409 for a foreign document whose base_version would have
    # been correct. Without this handler a ConflictException would surface as a 500
    # and the "never 409" assertion would pass for the wrong reason.
    app.add_exception_handler(ConflictException, conflict_exception_handler)
    app.dependency_overrides[get_token_service] = lambda: _RejectingTokenService()
    return app


class _RejectingTokenService:
    """Rejects every token. These tests override the owner dependency instead."""

    def read_access_subject(self, access_token):
        raise InvalidTokenException("token rejected by the test double")


def _returning(usecase):
    """A zero-argument override handing back `usecase`.

    A closure, NOT `lambda mock=usecase: mock`. FastAPI inspects an override's
    signature, so a parameter with a default becomes a *query parameter* and the
    mock the test holds records nothing while the endpoint still answers.
    """
    return lambda: usecase


class RefusingAiEditApp:
    """All seven usecases wired to refuse.

    Each one's first statement is `resolve_owned_document`, which raises the single
    id-free `NotFoundException(REFUSAL_MESSAGE)` for both the absent and the foreign
    document. Driving the mocks from that same exception keeps this layer's test
    honest about what the usecase layer actually does.
    """

    def __init__(self, app, usecases):
        self._app = app
        self._usecases = usecases

    async def invoke(self, route, document_id=None, json_body=_ROUTE_DEFAULT):
        """Send `route`, optionally overriding the document id or the request body.

        `json_body=None` is a meaningful value (send no body), so "use the route's own
        body" needs a sentinel rather than `None` as its default.
        """
        body = route.json_body if json_body is _ROUTE_DEFAULT else json_body
        async with AsyncClient(
            transport=ASGITransport(app=self._app), base_url="http://test"
        ) as client:
            return await client.request(
                route.method,
                route.path(document_id or uuid4()),
                json=body,
                headers=route.headers,
            )

    def times_reached(self, route):
        """How often the route's usecase was awaited — the guard runs there."""
        return self._usecases[route.provider_name].execute.await_count

    def resolution_of(self, route):
        """The keyword arguments the route's usecase was awaited with.

        An empty dict when it was never awaited, or when the route passed everything
        positionally — both are failures the caller asserts against a literal.
        """
        execute = self._usecases[route.provider_name].execute
        return dict(execute.await_args.kwargs) if execute.await_args else {}


@pytest.fixture
def refusing_app(ai_edit_app, mocker):
    usecases = {}
    for route in ALL_ROUTES:
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(side_effect=NotFoundException(REFUSAL_MESSAGE))
        usecases[route.provider_name] = usecase
        provider = getattr(router_module, route.provider_name)
        ai_edit_app.dependency_overrides[provider] = _returning(usecase)
    ai_edit_app.dependency_overrides[get_current_owner_id] = lambda: OWNER_ID
    return RefusingAiEditApp(ai_edit_app, usecases)
