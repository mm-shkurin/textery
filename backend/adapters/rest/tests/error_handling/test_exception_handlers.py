import logging

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from error_handling.exception_handlers import unhandled_exception_handler


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
