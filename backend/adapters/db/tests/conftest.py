import socket
from urllib.parse import urlsplit

import pytest

from statements.database_url import (
    _PROBE_TIMEOUT_SECONDS,
    TEST_DATABASE_URL_ENV_VAR,
    resolve_test_database_url,
)


@pytest.fixture(scope="session", autouse=True)
def require_database() -> None:
    """Skip this whole suite with a named reason when there is no database.

    Without it, `pytest` on a machine with no Postgres does not fail -- it
    *hangs*, because every fixture here opens a connection and waits out the
    driver's own timeout, once per test. A contributor running the documented
    `pytest` command sees no output and no reason, which reads as a broken
    checkout rather than a missing service. CI provides Postgres, so this probe
    passes there and gates nothing.
    """
    parts = urlsplit(resolve_test_database_url())
    host, port = parts.hostname or "localhost", parts.port or 5432
    try:
        with socket.create_connection((host, port), timeout=_PROBE_TIMEOUT_SECONDS):
            return
    except OSError as error:
        pytest.skip(
            f"no database listening at {host}:{port} ({error}). These are the adapter's "
            f"integration tests and need a real Postgres: set {TEST_DATABASE_URL_ENV_VAR}, "
            f"or run `pytest domain usecase` for the layers that need no database.",
            allow_module_level=True,
        )


# Imported for their side effect: pytest registers a fixture when the function
# object is present in the conftest namespace. They live in `statement_fixtures`
# because that list grows by one entry per Statements class, while what remains
# here -- what a test session connects to, and what gets truncated -- does not.
from statement_fixtures import (  # noqa: E402
    account_concurrency_statements,
    account_storage_statements,
    db_session,
    document_storage_statements,
    failed_attempt_concurrency_statements,
    generation_storage_statements,
    history_paging_statements,
    project_feed_statements,
    resend_ordering_statements,
    sql_alchemy_unit_of_work_statements,
    verification_code_storage_statements,
)

__all__ = [
    "account_concurrency_statements",
    "account_storage_statements",
    "db_session",
    "document_storage_statements",
    "failed_attempt_concurrency_statements",
    "generation_storage_statements",
    "history_paging_statements",
    "project_feed_statements",
    "require_database",
    "resend_ordering_statements",
    "sql_alchemy_unit_of_work_statements",
    "verification_code_storage_statements",
]
