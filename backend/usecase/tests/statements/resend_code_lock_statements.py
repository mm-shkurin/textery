from datetime import UTC, datetime, timedelta
from uuid import uuid4

from scope.register_request_scope import RegisterRequestScope

from auth.account import Account
from auth.register_user import RegisterUser
from auth.resend_code import ResendCode
from auth.verification_code import VerificationCode
from fake.auth.fake_account_repository import FakeAccountRepository
from fake.auth.fake_clock import FakeClock
from fake.auth.fake_password_hasher import FakePasswordHasher
from fake.auth.fake_unit_of_work import FakeUnitOfWork
from fake.auth.fake_verification_code_repository import FakeVerificationCodeRepository


class ResendCodeLockStatements:
    """Scenario 4.4 (usecase wiring): ResendCode must acquire the account row lock
    BEFORE the cooldown read, and thread the POST-lock account forward.

    The usecase test cannot exercise real concurrency (Fakes are single-threaded);
    it pins the CALL-SITE contract that makes the db serialization effective:
    (1) lock_for_update is called exactly once with the account id, BEFORE
    find_active_by_account_id (the cooldown read); (2) the account RETURNED by
    lock_for_update -- not the pre-lock one from find_by_email -- is what flows
    downstream (premortem CREDIBLE #2). Arrangement goes through the real
    RegisterUser, never by pre-seeding the Fakes.
    """

    T0 = datetime(2026, 7, 21, 12, 0, 0, tzinfo=UTC)
    PAST_COOLDOWN = timedelta(seconds=61)

    def __init__(self) -> None:
        self.account_repository = FakeAccountRepository()
        self.password_hasher = FakePasswordHasher()
        self.clock = FakeClock(fixed_now=self.T0)
        self.verification_code_repository = FakeVerificationCodeRepository()
        self.unit_of_work = FakeUnitOfWork()
        self.call_log: list[str] = []
        self.registered_email: str | None = None
        self.account_id = None
        self.locked_account: Account | None = None
        self.issued_code: VerificationCode | None = None

    async def given_a_pending_account_eligible_for_resend(self) -> None:
        self.clock.fixed_now = self.T0
        scope = RegisterRequestScope.builder()
        result = await RegisterUser(
            password_hasher=self.password_hasher,
            account_repository=self.account_repository,
            verification_code_repository=self.verification_code_repository,
            clock=self.clock,
        ).execute(
            email=scope.email,
            password=scope.password,
            confirm_password=scope.confirm_password,
        )
        self.registered_email = result.account.email
        self.account_id = result.account.id
        self.clock.fixed_now = self.T0 + self.PAST_COOLDOWN

    async def resend_with_the_call_order_recorded(self) -> None:
        # Share ONE ordering log across both Fakes so the relative order of
        # lock_for_update vs the cooldown read is observable. Reset it right before
        # execute so registration noise does not pollute the assertion.
        self.call_log.clear()
        self.account_repository.call_log = self.call_log
        self.verification_code_repository.call_log = self.call_log
        await self._execute_resend()

    async def resend_with_the_lock_returning_a_different_account(self) -> None:
        # premortem #2 lever: find_by_email resolves the registered account, but
        # lock_for_update RE-READS a DIFFERENT account (fresh id) -- as the real
        # SELECT ... FOR UPDATE would return the freshly-locked row. Correct wiring
        # threads THIS account forward, so the issued code carries its id, not the
        # pre-lock one.
        self.locked_account = Account.create(
            id=uuid4(),
            email="locked@example.ru",
            password_hash="hash",
            created_at=self.T0,
        )
        self.account_repository.lock_for_update_override_enabled = True
        self.account_repository.lock_for_update_result = self.locked_account
        self.issued_code = await self._execute_resend()

    async def _execute_resend(self) -> VerificationCode:
        return await ResendCode(
            account_repository=self.account_repository,
            verification_code_repository=self.verification_code_repository,
            clock=self.clock,
            unit_of_work=self.unit_of_work,
        ).execute(email=self.registered_email)

    def assert_lock_acquired_once_before_the_cooldown_read(self) -> None:
        assert self.account_repository.lock_for_update_calls == [self.account_id], (
            f"expected lock_for_update to be called exactly once with the account id "
            f"{self.account_id}, got {self.account_repository.lock_for_update_calls}"
        )
        assert self.call_log == ["lock_for_update", "find_active_by_account_id"], (
            f"expected the row lock to be acquired BEFORE the cooldown read, got call "
            f"order {self.call_log}"
        )

    def assert_issued_code_is_bound_to_the_locked_account(self) -> None:
        assert self.locked_account is not None and self.issued_code is not None
        assert self.issued_code.account_id == self.locked_account.id, (
            f"expected the resend to bind decisions to the POST-lock account "
            f"{self.locked_account.id} (lock_for_update's return), but the issued code "
            f"carries account_id {self.issued_code.account_id} -- the stale pre-lock "
            f"account from find_by_email ({self.account_id})"
        )
