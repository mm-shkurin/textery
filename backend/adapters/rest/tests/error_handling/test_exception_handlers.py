import logging

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from error_handling.exception_handlers import (
    unhandled_exception_handler,
    validation_exception_handler,
)
from shared.exceptions import ValidationException

# Named once: the test raises it and asserts the response echoes it verbatim, so
# a copy in each place could drift and still look like a passing round-trip.
RESEND_COOLDOWN_MESSAGE = (
    "A verification code was recently sent. Please wait before requesting another."
)


class TestValidationExceptionHandler:
    """A ValidationException is mapped to the {error_code, message} envelope at HTTP 400."""

    async def test_should_return_400_with_error_code_and_message(self):
        app = FastAPI()

        @app.get("/invalid")
        async def invalid() -> None:
            raise ValidationException(
                error_code="INVALID_EMAIL", message="The email address is not valid."
            )

        app.add_exception_handler(ValidationException, validation_exception_handler)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/invalid")

        assert response.status_code == 400, f"expected 400, got {response.status_code}"
        assert response.json() == {
            "error_code": "INVALID_EMAIL",
            "message": "The email address is not valid.",
        }, f"unexpected response body {response.json()}"

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

    async def test_should_return_409_when_error_code_is_already_verified(self):
        app = FastAPI()

        @app.get("/already-verified")
        async def already_verified() -> None:
            raise ValidationException(
                error_code="ALREADY_VERIFIED", message="The account is already verified."
            )

        app.add_exception_handler(ValidationException, validation_exception_handler)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/already-verified")

        assert response.status_code == 409, f"expected 409, got {response.status_code}"
        assert response.json() == {
            "error_code": "ALREADY_VERIFIED",
            "message": "The account is already verified.",
        }, f"unexpected response body {response.json()}"

    async def test_should_return_429_when_error_code_is_resend_cooldown_active(self):
        app = FastAPI()

        @app.get("/resend-cooldown")
        async def resend_cooldown() -> None:
            raise ValidationException(
                error_code="RESEND_COOLDOWN_ACTIVE",
                message=RESEND_COOLDOWN_MESSAGE,
            )

        app.add_exception_handler(ValidationException, validation_exception_handler)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/resend-cooldown")

        assert response.status_code == 429, f"expected 429, got {response.status_code}"
        assert response.json() == {
            "error_code": "RESEND_COOLDOWN_ACTIVE",
            "message": RESEND_COOLDOWN_MESSAGE,
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
        assert response.json() == {
            "error_code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred. Please try again.",
        }, f"unexpected body {response.json()}"
        assert "unexpected failure" not in response.text, (
            "the raised exception's own message must not reach the client -- it is "
            f"an arbitrary internal string. Got {response.text}"
        )
        assert any("unexpected failure" in record.message for record in caplog.records), (
            f"expected logged exception message to mention 'unexpected failure', "
            f"got {[r.message for r in caplog.records]}"
        )
        assert any(record.exc_info for record in caplog.records), (
            "expected traceback to be logged via exc_info"
        )
