import pytest

from statements.generation_lifecycle_statements import GenerationLifecycleStatements
from statements.generation_statements import GenerationStatements
from statements.login_statements import LoginStatements
from statements.refresh_statements import RefreshStatements
from statements.register_atomic_write_statements import RegisterAtomicWriteStatements
from statements.register_statements import RegisterStatements
from statements.resend_code_lock_statements import ResendCodeLockStatements
from statements.resend_code_statements import ResendCodeStatements
from statements.requeue_stale_generations_statements import RequeueStaleGenerationsStatements
from statements.verify_account_already_verified_statements import (
    VerifyAccountAlreadyVerifiedStatements,
)
from statements.verify_account_atomic_transition_statements import (
    VerifyAccountAtomicTransitionStatements,
)
from statements.verify_account_failure_statements import VerifyAccountFailureStatements
from statements.verify_account_idempotency_statements import (
    VerifyAccountIdempotencyStatements,
)
from statements.verify_account_statements import VerifyAccountStatements


@pytest.fixture
def register_statements():
    return RegisterStatements()


@pytest.fixture
def register_atomic_write_statements():
    return RegisterAtomicWriteStatements()


@pytest.fixture
def generation_statements():
    return GenerationStatements()


@pytest.fixture
def generation_lifecycle_statements():
    return GenerationLifecycleStatements()


@pytest.fixture
def requeue_stale_generations_statements():
    return RequeueStaleGenerationsStatements()


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
def resend_code_statements():
    return ResendCodeStatements()


@pytest.fixture
def resend_code_lock_statements():
    return ResendCodeLockStatements()


@pytest.fixture
def login_statements():
    return LoginStatements()


@pytest.fixture
def refresh_statements():
    return RefreshStatements()


@pytest.fixture
def verify_account_failure_statements():
    return VerifyAccountFailureStatements()
