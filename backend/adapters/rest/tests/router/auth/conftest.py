import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from error_handling.exception_handlers import validation_exception_handler
from router.auth import auth_router as auth_router_module
from shared.exceptions import ValidationException

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
    export yet raises during collection and aborts every test in this directory,
    not just the one that needs the provider (verified: 1 collection error, 0 of
    16 tests run). Resolving on call keeps a not-yet-exported provider scoped to
    the test that needs it, failing it with an AttributeError that names the
    missing symbol. The constraint is only "not at conftest import time" -- the
    lookup does not otherwise depend on being inside `_make`.
    """

    def _make(mock_usecase):
        provider = getattr(auth_router_module, provider_name)
        app.dependency_overrides[provider] = lambda: mock_usecase
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    return _make


@pytest.fixture
def register_client(auth_app):
    """Factory: `async with register_client(mock_usecase) as client:`"""
    return _client_factory(auth_app, "get_register_user_usecase")


@pytest.fixture
def verify_client(auth_app):
    """Factory: `async with verify_client(mock_usecase) as client:`"""
    return _client_factory(auth_app, "get_verify_account_usecase")


@pytest.fixture
def login_client(auth_app):
    """Factory: `async with login_client(mock_usecase) as client:`"""
    return _client_factory(auth_app, "get_login_user_usecase")


@pytest.fixture
def refresh_client(auth_app):
    """Factory: `async with refresh_client(mock_usecase) as client:`"""
    return _client_factory(auth_app, "get_refresh_access_token_usecase")


@pytest.fixture
def resend_client(auth_app):
    """Factory: `async with resend_client(mock_usecase) as client:`"""
    return _client_factory(auth_app, "get_resend_code_usecase")


@pytest.fixture
def rate_limited_login_client(auth_app):
    """`login_client`, plus a guard whose counter is small enough to trip in a test.

    The app-wide default guard never throttles -- the bound is a deployment
    concern -- so a test that wants to observe the refusal has to supply the
    store, exactly as the composition root does.
    """
    from credential_rate_limit_fixtures import CountingRateLimiter

    from auth.rate_limiting import CredentialRateGuard
    from router.auth import credential_rate_limit

    guard = CredentialRateGuard(rate_limiter=CountingRateLimiter())
    auth_app.dependency_overrides[credential_rate_limit.get_credential_rate_guard] = lambda: guard
    return _client_factory(auth_app, "get_login_user_usecase")
