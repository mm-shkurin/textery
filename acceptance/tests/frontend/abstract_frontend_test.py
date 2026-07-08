import pytest


@pytest.mark.frontend
class AbstractFrontendTest:
    """Base class for frontend acceptance tests: black-box browser tests against the
    real running React app (via Selenium `webdriver`/`app_url`), never a
    component-level or in-process shortcut.
    """
