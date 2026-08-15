"""Projects-feed Statements fixtures (story 12).

Kept out of conftest.py so that file stays under the 200-line cap; the names are
imported back into conftest, so pytest discovers them exactly as if they were defined
there. Relies on conftest having inserted the acceptance dir onto sys.path first, which
makes the `statements.*` import below resolve.
"""

import pytest_asyncio

from statements.project_feed_statements import ProjectFeedStatements


@pytest_asyncio.fixture
def project_feed_statements(application_client):
    return ProjectFeedStatements(application_client)
