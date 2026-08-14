import pytest

from statements.avatar_statements import AvatarStatements
from statements.delete_account_statements import DeleteAccountStatements
from statements.deletion_confirmation_statements import DeletionConfirmationStatements
from statements.generation_lifecycle_statements import GenerationLifecycleStatements
from statements.generation_prompt_failure_statements import GenerationPromptFailureStatements
from statements.generation_statements import GenerationStatements
from statements.get_profile_statements import GetProfileStatements
from statements.login_failed_attempt_statements import LoginFailedAttemptStatements
from statements.login_lockout_statements import LoginLockoutStatements
from statements.login_statements import LoginStatements
from statements.port_shape_statements import PortShapeStatements
from statements.project_feed_row_statements import ProjectFeedRowStatements
from statements.project_feed_statements import ProjectFeedStatements
from statements.project_item_shape_statements import ProjectItemShapeStatements
from statements.refresh_statements import RefreshStatements
from statements.register_atomic_write_statements import RegisterAtomicWriteStatements
from statements.register_statements import RegisterStatements
from statements.rename_account_statements import RenameAccountStatements
from statements.requeue_stale_generations_statements import RequeueStaleGenerationsStatements
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
def generation_prompt_failure_statements():
    return GenerationPromptFailureStatements()


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
def project_feed_statements():
    return ProjectFeedStatements()


@pytest.fixture
def project_feed_row_statements():
    return ProjectFeedRowStatements()


@pytest.fixture
def project_item_shape_statements():
    return ProjectItemShapeStatements()


@pytest.fixture
def port_shape_statements():
    return PortShapeStatements()


@pytest.fixture
def verify_account_failure_statements():
    return VerifyAccountFailureStatements()


@pytest.fixture
def get_profile_statements():
    return GetProfileStatements()


@pytest.fixture
def rename_account_statements():
    return RenameAccountStatements()


@pytest.fixture
def avatar_statements():
    return AvatarStatements()


@pytest.fixture
def delete_account_statements():
    return DeleteAccountStatements()


@pytest.fixture
def deletion_confirmation_statements():
    return DeletionConfirmationStatements()
