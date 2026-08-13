"""Story-13 profile Statements fixture, in its own module for the 200-line cap.

Same arrangement the generation, export and page-settings fixtures already use:
`conftest.py` re-imports the name so pytest discovers it as a conftest fixture.
"""

import pytest_asyncio

from statements.profile_statements import ProfileStatements


@pytest_asyncio.fixture
def profile_statements(application_client):
    return ProfileStatements(application_client)
