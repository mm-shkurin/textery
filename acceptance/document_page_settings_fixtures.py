"""Page-settings Statements fixtures (story 10).

Split out of conftest.py to keep that file under the 200-line cap, exactly as
document_export_fixtures.py is. These names are imported back into conftest, so
pytest discovers them as if they were defined there.
"""

import pytest_asyncio

from statements.document_page_settings_read_statements import (
    DocumentPageSettingsReadStatements,
)


@pytest_asyncio.fixture
def document_page_settings_read_statements(application_client):
    return DocumentPageSettingsReadStatements(application_client)
