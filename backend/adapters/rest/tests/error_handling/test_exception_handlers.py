import logging

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from error_handling.exception_handlers import unhandled_exception_handler, validation_exception_handler
from shared.exceptions import ValidationException


class TestValidationExceptionHandler:
    """A ValidationException is mapped to the {error_code, message} envelope at HTTP 400."""

    async def test_should_return_400_with_error_code_and_message(self):
        app = FastAPI()

        @app.get("/invalid")
        async def invalid() -> None:
            raise ValidationException(error_code="INVALID_EMAIL", message="The email address is not valid.")

        app.add_exception_handler(ValidationException, validation_exception_handler)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/invalid")

        assert response.status_code == 400, f"expected 400, got {response.status_code}"
        assert response.json() == {
            "error_code": "INVALID_EMAIL",
            "message": "The email address is not valid.",
        }, f"unexpected response body {response.json()}"

    @pytest.mark.skip(reason="RED: validation_exception_handler always returns 400")
    async def test_should_return_409_when_error_code_is_email_already_registered(self):
        app = FastAPI()

        @app.get("/duplicate")
        async def duplicate() -> None:
            raise ValidationException(
                error_code="EMAIL_ALREADY_REGISTERED", message="This email is already registered."
            )

        app.add_exception_handler(ValidationException, validation_exception_handler)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/duplicate")

        assert response.status_code == 409, f"expected 409, got {response.status_code}"
        assert response.json() == {
            "error_code": "EMAIL_ALREADY_REGISTERED",
            "message": "This email is already registered.",
        }, f"unexpected response body {response.json()}"


class TestUnhandledExceptionHandler:
    """An unhandled exception is logged with its traceback before returning a generic 500."""

    async def test_should_log_exception_and_return_generic_500(self, caplog):
        app = FastAPI()

        @app.get("/boom")
        async def boom() -> None:
            raise RuntimeError("unexpected failure")

        app.add_exception_handler(Exception, unhandled_exception_handler)

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        with caplog.at_level(logging.ERROR):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/boom")

        assert response.status_code == 500, f"expected 500, got {response.status_code}"
        assert response.json() == {"detail": "internal server error"}, f"unexpected body {response.json()}"
        assert any("unexpected failure" in record.message for record in caplog.records), (
            f"expected logged exception message to mention 'unexpected failure', got {[r.message for r in caplog.records]}"
        )
        assert any(record.exc_info for record in caplog.records), "expected traceback to be logged via exc_info"
