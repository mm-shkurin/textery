"""Story-13 profile BROWSER Statements fixtures, in their own module for the 200-line cap.

The API-level story-13 fixtures live in `profile_fixtures.py`; these are the
Selenium ones. Same arrangement every other feature already uses: `conftest.py`
re-imports the names so pytest discovers them as conftest fixtures.
"""

import pytest

from statements.frontend.profile.profile_avatar_statements import ProfileAvatarStatements
from statements.frontend.profile.profile_deletion_statements import ProfileDeletionStatements
from statements.frontend.profile.profile_page_statements import ProfilePageStatements
from statements.frontend.profile.profile_theme_statements import ProfileThemeStatements


@pytest.fixture
def profile_page_statements():
    return ProfilePageStatements()


@pytest.fixture
def profile_avatar_statements():
    statements = ProfileAvatarStatements()
    yield statements
    # The picture is written to a temporary directory; a test that fails mid-upload would
    # otherwise leave one behind per run.
    statements.cleanup()


@pytest.fixture
def profile_theme_statements():
    return ProfileThemeStatements()


@pytest.fixture
def profile_deletion_statements():
    return ProfileDeletionStatements()
