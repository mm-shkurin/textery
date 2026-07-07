import pytest


@pytest.mark.backend
class AbstractBackendTest:
    """Base class for backend acceptance tests: black-box HTTP tests against the

    real running FastAPI application (via `application_client`), never an
    in-process ASGI shortcut.
    """
