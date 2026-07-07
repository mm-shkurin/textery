import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest_asyncio

from clients.application.application_client import ApplicationClient
from statements.generation_statements import GenerationStatements


@pytest_asyncio.fixture
async def application_client():
    client = ApplicationClient()
    yield client
    await client.close()


@pytest_asyncio.fixture
def generation_statements(application_client):
    return GenerationStatements(application_client)
