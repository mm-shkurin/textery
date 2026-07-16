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


@pytest.fixture
def auth_app():
    app = FastAPI()
    app.include_router(auth_router)
    app.add_exception_handler(ValidationException, validation_exception_handler)
    return app


def _client_factory(app, provider_name):
    """Build a factory wiring `mock_usecase` in as the override for the router's
    `provider_name` DI provider, returning an AsyncClient bound to `app`.

    The provider is resolved at call time rather than at import time. This module
    is a conftest, so an import-time lookup of a provider the router does not
    export yet aborts collection for every test in this directory. Resolving on
    call keeps a missing provider scoped to the test that actually needs it, and
    surfaces it as an AttributeError naming the provider -- rather than as a
    silently skipped override, which would let a route that never calls its
    usecase still appear to pass.
    """

    def _make(mock_usecase):
        provider = getattr(auth_router_module, provider_name)
        app.dependency_overrides[provider] = lambda: mock_usecase
        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://test")

    return _make


@pytest.fixture
def register_client(auth_app):
    """Factory: `async with register_client(mock_usecase) as client:`"""
    return _client_factory(auth_app, "get_register_user_usecase")


@pytest.fixture
def verify_client(auth_app):
    """Factory: `async with verify_client(mock_usecase) as client:`"""
    return _client_factory(auth_app, "get_verify_account_usecase")
