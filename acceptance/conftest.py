import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest
import pytest_asyncio
from selenium import webdriver as selenium_webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions

from clients.application.application_client import ApplicationClient
from statements.auth_statements import AuthStatements
from statements.frontend.landing_page_statements import LandingPageStatements
from statements.frontend.generation.chat_workspace_statements import ChatWorkspaceStatements
from statements.frontend.responsive_statements import ResponsiveStatements
from statements.generation_statements import GenerationStatements

# iPhone 12/13-class viewport — the smallest common real-device width the
# "design for phone" scenarios must not horizontally overflow at.
MOBILE_WINDOW_SIZE = "390,844"


@pytest_asyncio.fixture
async def application_client():
    client = ApplicationClient()
    yield client
    await client.close()


@pytest_asyncio.fixture
def generation_statements(application_client):
    return GenerationStatements(application_client)


@pytest_asyncio.fixture
def auth_statements(application_client):
    return AuthStatements(application_client)


@pytest.fixture
def app_url():
    return f"http://127.0.0.1:{os.environ.get('FRONTEND_PORT', '5173')}"


@pytest.fixture
def webdriver():
    options = ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1400,1000")
    driver = selenium_webdriver.Chrome(options=options)
    yield driver
    driver.quit()


@pytest.fixture
def mobile_webdriver():
    options = ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument(f"--window-size={MOBILE_WINDOW_SIZE}")
    driver = selenium_webdriver.Chrome(options=options)
    yield driver
    driver.quit()


@pytest.fixture
def landing_page_statements():
    return LandingPageStatements()


@pytest.fixture
def responsive_statements():
    return ResponsiveStatements()


@pytest.fixture
def chat_workspace_statements():
    return ChatWorkspaceStatements()
