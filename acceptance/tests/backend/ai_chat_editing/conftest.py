import pytest_asyncio

from clients.application.document_edit_client import DocumentEditClient
from statements.ai_edit.ai_edit_cross_document_statements import (
    AiEditCrossDocumentStatements,
)
from statements.ai_edit.ai_edit_guard_statements import AiEditGuardStatements

# Story 19's fixtures live here rather than in the root conftest, which is already
# over the 200-line file limit — a nested conftest is the same fixture scope to
# pytest and keeps the oversized file from growing further.


@pytest_asyncio.fixture
async def document_edit_client():
    client = DocumentEditClient()
    yield client
    await client.close()


@pytest_asyncio.fixture
def ai_edit_guard_statements(application_client, document_edit_client):
    return AiEditGuardStatements(application_client, document_edit_client)


@pytest_asyncio.fixture
def ai_edit_cross_document_statements(application_client, document_edit_client):
    return AiEditCrossDocumentStatements(application_client, document_edit_client)
