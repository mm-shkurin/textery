"""Where the db suite connects, and the guard that keeps it off a real database.

Its own module so that `conftest` and `statement_fixtures` can both call it
without importing each other. They briefly did import each other -- the cycle
resolved by accident of definition order, which is the kind of thing that works
until someone moves a line.

The guard below is the reason this is worth being careful with; it is moved here
verbatim, not rewritten.
"""

import os
from urllib.parse import urlsplit

TEST_DATABASE_URL_ENV_VAR = "TEST_DATABASE_URL"
# `textery_test`, NOT `textery`. This suite TRUNCATEs every table between
# fixtures, so pointing it at the database the running app uses erases whatever a
# developer had in their local stack -- accounts, documents, generations, the lot.
# The default used to be `textery`, and on 2026-08-06 that is exactly what
# happened: a full `pytest backend/` run against a live stack wiped the dev data,
# and the first symptom was the app answering 401 to a password that had worked a
# minute earlier.
DEFAULT_TEST_DATABASE_URL = "postgresql://textery:change-me@localhost:5432/textery_test"

# A database this suite is allowed to empty must say so in its name. A blunt rule
# on purpose: the failure it prevents is silent and unrecoverable, and every
# subtler check ("is anything running against it?") answers "no" for the seconds
# between two requests.
_TEST_DATABASE_NAME_MARKER = "test"
# Short on purpose: this is a liveness probe, not the connection itself. The
# answer is "is anything listening", and anything listening answers instantly.
_PROBE_TIMEOUT_SECONDS = 3


def resolve_test_database_url() -> str:
    """Point the adapter's own `create_engine()` at the test database.

    Refuses a target whose database name does not mark itself as a test database.
    This suite empties every table it touches; a mistyped or inherited
    TEST_DATABASE_URL pointing at a real one destroys data with no error and no
    way back, and the loss surfaces later as an unrelated-looking authentication
    failure.
    """
    os.environ.setdefault(TEST_DATABASE_URL_ENV_VAR, DEFAULT_TEST_DATABASE_URL)
    url = os.environ[TEST_DATABASE_URL_ENV_VAR]
    database_name = (urlsplit(url).path or "").lstrip("/")
    if _TEST_DATABASE_NAME_MARKER not in database_name.lower():
        raise RuntimeError(
            f"{TEST_DATABASE_URL_ENV_VAR} points at database {database_name!r}, which is "
            f"not marked as a test database. This suite TRUNCATEs every table between "
            f"fixtures. Point it at a database whose name contains "
            f"{_TEST_DATABASE_NAME_MARKER!r} (the default is {DEFAULT_TEST_DATABASE_URL})."
        )
    os.environ["DATABASE_URL"] = url
    return url
