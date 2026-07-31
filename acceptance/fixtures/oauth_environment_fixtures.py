"""The OAuth invariant-gate environment contract (see acceptance/tests/backend/oauth/).

Split out of the root conftest, which had grown past the 200-line file limit.
Registered as a plugin from that conftest, so fixture scope is unchanged.
"""

import asyncio
import os

import pytest
import pytest_asyncio

HANDOFF_CODE_TTL_ENV_VAR = "OAUTH_HANDOFF_CODE_TTL_SECONDS"
PROVIDER_SECRET_ENV_VAR = "YANDEX_CLIENT_SECRET"
MAX_TESTABLE_TTL_SECONDS = 10


@pytest_asyncio.fixture
async def expired_code(oauth_statements):
    """A handoff code that has outlived its TTL.

    The TTL is real production config, not a test switch — the acceptance stack runs a
    deliberately tiny one so the boundary is observable in seconds. A long TTL makes
    this invariant untestable rather than passing, so it fails loudly instead.
    """
    ttl_seconds = int(os.environ.get(HANDOFF_CODE_TTL_ENV_VAR, "0"))
    assert 0 < ttl_seconds <= MAX_TESTABLE_TTL_SECONDS, (
        f"the TTL invariant needs {HANDOFF_CODE_TTL_ENV_VAR} set to at most "
        f"{MAX_TESTABLE_TTL_SECONDS}s for the acceptance stack, got {ttl_seconds!r}"
    )
    code = await oauth_statements.handoff_code()
    await asyncio.sleep(ttl_seconds + 1)
    return code


@pytest.fixture
def provider_secret():
    secret = os.environ.get(PROVIDER_SECRET_ENV_VAR, "")
    assert secret, (
        f"the log-leak invariant needs the real {PROVIDER_SECRET_ENV_VAR} in the "
        "acceptance environment — it is the string that must never appear in a log"
    )
    return secret
