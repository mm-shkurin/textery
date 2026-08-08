"""Fixtures for the auth usecases.

Split out of one root `conftest.py` that carried every Statements class in the
module. That file grew by one fixture per scenario and was within twenty lines of
the 200-line hard limit; more to the point, every test in the module paid for
importing every Statements class, so an import error in a revision-guard file
surfaced while running the login tests. Each directory now declares what it uses.
"""

import pytest

from statements.login_failed_attempt_statements import LoginFailedAttemptStatements
from statements.login_lockout_statements import LoginLockoutStatements
from statements.login_statements import LoginStatements
from statements.refresh_statements import RefreshStatements
from statements.register_atomic_write_statements import RegisterAtomicWriteStatements
from statements.register_statements import RegisterStatements
from statements.resend_code_lock_statements import ResendCodeLockStatements
from statements.resend_code_statements import ResendCodeStatements
from statements.resend_verified_statements import ResendVerifiedStatements
from statements.verify_account_already_verified_statements import (
    VerifyAccountAlreadyVerifiedStatements,
)
from statements.verify_account_atomic_transition_statements import (
    VerifyAccountAtomicTransitionStatements,
)
from statements.verify_account_failure_statements import VerifyAccountFailureStatements
from statements.verify_account_idempotency_statements import VerifyAccountIdempotencyStatements
from statements.verify_account_statements import VerifyAccountStatements


@pytest.fixture
def register_statements():
    return RegisterStatements()


@pytest.fixture
def register_atomic_write_statements():
    return RegisterAtomicWriteStatements()


@pytest.fixture
def verify_account_statements():
    return VerifyAccountStatements()


@pytest.fixture
def verify_account_idempotency_statements():
    return VerifyAccountIdempotencyStatements()


@pytest.fixture
def verify_account_already_verified_statements():
    return VerifyAccountAlreadyVerifiedStatements()


@pytest.fixture
def verify_account_atomic_transition_statements():
    return VerifyAccountAtomicTransitionStatements()


@pytest.fixture
def verify_account_failure_statements():
    return VerifyAccountFailureStatements()


@pytest.fixture
def resend_code_statements():
    return ResendCodeStatements()


@pytest.fixture
def resend_code_lock_statements():
    return ResendCodeLockStatements()


@pytest.fixture
def resend_verified_statements():
    return ResendVerifiedStatements()


@pytest.fixture
def login_statements():
    return LoginStatements()


@pytest.fixture
def login_failed_attempt_statements():
    return LoginFailedAttemptStatements()


@pytest.fixture
def login_lockout_statements():
    return LoginLockoutStatements()


@pytest.fixture
def refresh_statements():
    return RefreshStatements()
