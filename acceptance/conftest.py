import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest_asyncio

from clients.application.application_client import ApplicationClient
from statements.auth_statements import AuthStatements
from statements.generation_statements import GenerationStatements
from statements.login_statements import LoginStatements
from statements.oauth_statements import OAuthStatements
from statements.resend_statements import ResendStatements
from statements.verify_statements import VerifyStatements

# The rest of the fixture set lives in `fixtures/` rather than here: this file is the
# rootdir conftest and had grown past the 200-line limit. Plugin registration puts the
# fixtures in exactly the same scope they were in when they were defined inline.
pytest_plugins = (
    "fixtures.browser_fixtures",
    "fixtures.frontend_statements_fixtures",
    "fixtures.oauth_environment_fixtures",
)


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


@pytest_asyncio.fixture
def verify_statements(application_client):
    return VerifyStatements(application_client)


@pytest_asyncio.fixture
def resend_statements(application_client):
    return ResendStatements(application_client)


@pytest_asyncio.fixture
def login_statements(application_client):
    return LoginStatements(application_client)


@pytest_asyncio.fixture
def oauth_statements(application_client):
    return OAuthStatements(application_client)
