import pytest

from statements.ai_edit_refusal_log_statements import AiEditRefusalLogStatements
from statements.ai_edit_scope_guard_statements import AiEditScopeGuardStatements
from statements.ai_edit_store_failure_statements import AiEditStoreFailureStatements
from statements.document_scope_guard_statements import DocumentScopeGuardStatements
from statements.generation_lifecycle_statements import GenerationLifecycleStatements
from statements.generation_statements import GenerationStatements
from statements.login_failed_attempt_statements import LoginFailedAttemptStatements
from statements.login_lockout_statements import LoginLockoutStatements
from statements.login_statements import LoginStatements
from statements.refresh_statements import RefreshStatements
from statements.refusal_record_shape_statements import RefusalRecordShapeStatements
from statements.register_atomic_write_statements import RegisterAtomicWriteStatements
from statements.register_statements import RegisterStatements
from statements.requeue_stale_generations_statements import RequeueStaleGenerationsStatements
from statements.resend_code_lock_statements import ResendCodeLockStatements
from statements.resend_code_statements import ResendCodeStatements
from statements.resend_verified_statements import ResendVerifiedStatements
from statements.revision_number_range_statements import RevisionNumberRangeStatements
from statements.revision_outage_statements import RevisionOutageStatements
from statements.revision_refusal_log_statements import RevisionRefusalLogStatements
from statements.revision_scope_guard_statements import RevisionScopeGuardStatements
from statements.revision_silence_statements import RevisionSilenceStatements
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
def document_scope_guard_statements():
    return DocumentScopeGuardStatements()


@pytest.fixture
def ai_edit_scope_guard_statements():
    return AiEditScopeGuardStatements()


@pytest.fixture
def ai_edit_store_failure_statements():
    return AiEditStoreFailureStatements()


@pytest.fixture
def ai_edit_refusal_log_statements():
    statements = AiEditRefusalLogStatements()
    yield statements
    statements.stop_collecting()


@pytest.fixture
def revision_scope_guard_statements():
    return RevisionScopeGuardStatements()


@pytest.fixture
def revision_number_range_statements():
    return RevisionNumberRangeStatements()


@pytest.fixture
def revision_outage_statements():
    return RevisionOutageStatements()


@pytest.fixture
def revision_refusal_log_statements():
    statements = RevisionRefusalLogStatements()
    yield statements
    statements.stop_collecting()


@pytest.fixture
def revision_silence_statements():
    statements = RevisionSilenceStatements()
    yield statements
    statements.stop_collecting()


@pytest.fixture
def refusal_record_shape_statements(
    ai_edit_refusal_log_statements, revision_refusal_log_statements
):
    return RefusalRecordShapeStatements(
        ai_edit_refusal_log_statements, revision_refusal_log_statements
    )


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


@pytest.fixture
def verify_account_failure_statements():
    return VerifyAccountFailureStatements()
