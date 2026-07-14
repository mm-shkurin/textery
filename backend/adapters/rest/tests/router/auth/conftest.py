import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from shared.exceptions import ValidationException
from error_handling.exception_handlers import validation_exception_handler

auth_router_module = pytest.importorskip(
    "router.auth.auth_router",
    reason="RED: router.auth.auth_router module does not exist (ModuleNotFoundError)",
)
auth_router = auth_router_module.router
get_register_user_usecase = auth_router_module.get_register_user_usecase


@pytest.fixture
def register_app():
    app = FastAPI()
    app.include_router(auth_router)
    app.add_exception_handler(ValidationException, validation_exception_handler)
    return app


@pytest.fixture
def register_client(register_app):
    """Return a factory building an AsyncClient with the usecase mock wired in.

    Usage: `async with register_client(mock_usecase) as client:`
    """

    def _make(mock_usecase):
        register_app.dependency_overrides[get_register_user_usecase] = lambda: mock_usecase
        transport = ASGITransport(app=register_app)
        return AsyncClient(transport=transport, base_url="http://test")

    return _make
