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
# object is present in the conftest namespace.
#
# A STAR import over statement_fixtures' computed `__all__`, not a hand-kept list.
# The list was kept by hand in two places here, and a fixture added there but
# forgotten here does not fail at collection - it fails at SETUP of whichever test
# asks for it, "fixture not found", listing the ones that were remembered. Four
# fixtures sat in that state, and only CI could see it: without Postgres the whole
# suite skips.
#
# TWO modules, split by what each fixture needs: `statement_fixtures` holds the ones
# that share one `db_session`, `engine_scoped_fixtures` the ones whose claim is about
# what a DIFFERENT session sees. Both are star-imported for the same reason.
from engine_scoped_fixtures import *  # noqa: E402,F401,F403
from engine_scoped_fixtures import __all__ as _engine_fixture_names  # noqa: E402
from statement_fixtures import *  # noqa: E402,F401,F403
from statement_fixtures import __all__ as _session_fixture_names  # noqa: E402

# `require_database` lives here, not there, so it is added on top of whatever the
# fixture modules export rather than re-listed alongside them.
__all__ = [*_session_fixture_names, *_engine_fixture_names, "require_database"]
