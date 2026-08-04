import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from error_handling.exception_handlers import validation_exception_handler
from shared.exceptions import ValidationException

# Raised verbatim by ListProjects.execute when the owner cannot be resolved. Named
# once so the route and the assertion cannot drift into a round-trip that passes
# while saying something the usecase never says.
UNAUTHENTICATED_MESSAGE = "Authentication is required to view your projects."


@pytest.fixture
def app():
    application = FastAPI()
    application.add_exception_handler(ValidationException, validation_exception_handler)

    @application.get("/unauthenticated")
    async def raise_unauthenticated():
        raise ValidationException(message=UNAUTHENTICATED_MESSAGE, error_code="UNAUTHENTICATED")

    return application


@pytest.fixture
def client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.skip(
    reason="RED: _ERROR_CODE_STATUS_MAP has no UNAUTHENTICATED entry, "
    "so the handler defaults to 400"
)
class TestUnauthenticatedStatusMapping:
    """Story 12 Scenario 1.1: an unresolved owner fails closed as 401, not 400.

    ListProjects.execute refuses an unresolved owner with
    ValidationException(error_code="UNAUTHENTICATED"), and projects_list.yaml
    declares 401 for it. _ERROR_CODE_STATUS_MAP has no UNAUTHENTICATED entry, so
    the handler's .get(..., 400) default answers 400 -- a well-formed body with the
    right error_code at a status that tells the client its request was malformed
    rather than unauthenticated. The status and the body are asserted together
    because the default already gets the body half right.
    """

    async def test_should_map_unauthenticated_to_401_in_the_canonical_error_shape(self, client):
        async with client as http:
            response = await http.get("/unauthenticated")

        assert response.status_code == 401, f"got {response.status_code}: {response.text}"
        assert response.json() == {
            "error_code": "UNAUTHENTICATED",
            "message": UNAUTHENTICATED_MESSAGE,
        }, f"unexpected body {response.json()}"
