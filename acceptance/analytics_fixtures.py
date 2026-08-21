"""Analytics-ingest Statements fixtures (story 14).

Kept out of conftest.py so that file stays under the 200-line cap; registered there
through `pytest_plugins`, so pytest discovers these exactly as if they were defined
in conftest.
"""

import pytest_asyncio

from statements.analytics_ingest_statements import AnalyticsIngestStatements


@pytest_asyncio.fixture
def analytics_ingest_statements(application_client):
    return AnalyticsIngestStatements(application_client)
