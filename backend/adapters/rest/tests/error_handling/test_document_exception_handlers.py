import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from error_handling.exception_handlers import (
    conflict_exception_handler,
    not_found_exception_handler,
    validation_exception_handler,
)
from shared.exceptions import ConflictException, NotFoundException, ValidationException


@pytest.fixture
def app():
    application = FastAPI()
    application.add_exception_handler(ValidationException, validation_exception_handler)
    application.add_exception_handler(NotFoundException, not_found_exception_handler)
    application.add_exception_handler(ConflictException, conflict_exception_handler)

    @application.get("/not-found")
    async def raise_not_found():
        # Raised with the real message shape the usecases use — an internal id.
        raise NotFoundException("document 3f1b0c9e-1111-2222-3333-444455556666 not found")

    @application.get("/conflict")
    async def raise_conflict():
        raise ConflictException("document 3f1b0c9e-1111-2222-3333-444455556666 was modified concurrently")

    @application.get("/unauthorized")
    async def raise_unauthorized():
        raise ValidationException(error_code="UNAUTHORIZED", message="Authentication is required.")

    return application


@pytest.fixture
def client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class TestNotFoundHandler:
    """Scenarios 4.2 / 5.3: a missing document reports not found.

    Before this, NotFoundException had no handler at all and fell through to the
    500 handler — every "document not found" was an internal server error.
    """

    async def test_should_return_404_in_the_canonical_error_shape(self, client):
        async with client as http:
            response = await http.get("/not-found")

        assert response.status_code == 404, f"got {response.status_code}: {response.text}"
        assert response.json() == {
            "error_code": "NOT_FOUND",
            "message": "The requested resource was not found.",
        }, f"unexpected body {response.json()}"

    async def test_should_not_leak_the_exception_message(self, client):
        # Security 5.1: no internal id shape in the body. The usecases raise
        # NotFoundException(f"document {id} not found"), so echoing str(exc) would
        # publish exactly what 5.1 forbids. The handler must emit a fixed message.
        async with client as http:
            response = await http.get("/not-found")

        assert "3f1b0c9e" not in response.text, f"internal id leaked: {response.text}"
        assert "document" not in response.text.lower()


class TestConflictHandler:
    """Scenario 6.3: a stale version reports a version conflict."""

    async def test_should_return_409_in_the_canonical_error_shape(self, client):
        async with client as http:
            response = await http.get("/conflict")

        assert response.status_code == 409, f"got {response.status_code}: {response.text}"
        assert response.json() == {
            "error_code": "VERSION_CONFLICT",
            "message": "The document was modified by another save. Refetch and retry.",
        }, f"unexpected body {response.json()}"

    async def test_should_not_leak_the_exception_message(self, client):
        async with client as http:
            response = await http.get("/conflict")

        assert "3f1b0c9e" not in response.text, f"internal id leaked: {response.text}"


class TestUnauthorizedStatusMapping:
    """The 401 rides the existing ValidationException handler — no new machinery."""

    async def test_should_map_unauthorized_to_401(self, client):
        async with client as http:
            response = await http.get("/unauthorized")

        assert response.status_code == 401, f"got {response.status_code}: {response.text}"
        assert response.json() == {
            "error_code": "UNAUTHORIZED",
            "message": "Authentication is required.",
        }
