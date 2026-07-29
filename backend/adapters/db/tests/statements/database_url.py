"""Where the adapter's integration tests get their database.

The env-setup was written out in `conftest.py` and again in three test modules that
build their own engine, each carrying its own copy of the default URL -- so pointing
the suite at a different database meant finding all four, and a copy that drifted
would silently run against the wrong one.

`create_engine()` reads `DATABASE_URL`, so this is not merely reading a value: it
assigns `TEST_DATABASE_URL` onto `DATABASE_URL`. That is why callers go through here
rather than reading the env var themselves.

The module is deliberately **not** named `test_database.py`: pytest would collect it
and run the configuration helper as a test.
"""

import os

TEST_DATABASE_URL_ENV_VAR = "TEST_DATABASE_URL"
DATABASE_URL_ENV_VAR = "DATABASE_URL"
DEFAULT_TEST_DATABASE_URL = "postgresql://textery:change-me@localhost:5432/textery"


def configure_test_database_url() -> str:
    """Point the adapter's own `create_engine()` at the test database."""
    os.environ.setdefault(TEST_DATABASE_URL_ENV_VAR, DEFAULT_TEST_DATABASE_URL)
    os.environ[DATABASE_URL_ENV_VAR] = os.environ[TEST_DATABASE_URL_ENV_VAR]
    return os.environ[TEST_DATABASE_URL_ENV_VAR]
