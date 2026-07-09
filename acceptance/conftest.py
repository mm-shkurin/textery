import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest
import pytest_asyncio
from selenium import webdriver as selenium_webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions

from clients.application.application_client import ApplicationClient
from statements.frontend.landing_page_statements import LandingPageStatements
from statements.frontend.generation.chat_workspace_statements import ChatWorkspaceStatements
from statements.generation_statements import GenerationStatements


@pytest_asyncio.fixture
async def application_client():
    client = ApplicationClient()
    yield client
    await client.close()


@pytest_asyncio.fixture
def generation_statements(application_client):
    return GenerationStatements(application_client)


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
def landing_page_statements():
    return LandingPageStatements()


@pytest.fixture
def chat_workspace_statements():
    return ChatWorkspaceStatements()
