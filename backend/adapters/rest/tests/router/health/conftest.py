import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from router.health import health_router as health_router_module


@pytest.fixture
def health_app():
    """The health router alone, with no exception handlers registered.

    Deliberately bare. The endpoint must produce its own 503 rather than raise and
    be rescued by a handler -- an app that mounts this router without the project's
    handlers (or before them) still has to answer a probe correctly.
    """
    app = FastAPI()
    app.include_router(health_router_module.router)
    return app


@pytest.fixture
def create_health_client(health_app):
    def create(usecase):
        health_app.dependency_overrides[health_router_module.get_check_health_usecase] = lambda: (
            usecase
        )
        return AsyncClient(transport=ASGITransport(app=health_app), base_url="http://test")

    return create
