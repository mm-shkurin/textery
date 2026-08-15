from datetime import UTC, datetime
from uuid import UUID, uuid4

from auth.account import Account
from fake.auth.fake_account_repository import FakeAccountRepository
from fake.auth.fake_clock import FakeClock
from fake.auth.fake_password_hasher import FakePasswordHasher
from fake.auth.fake_unit_of_work import FakeUnitOfWork
from shared.exceptions import ValidationException
from statements.arranged import arranged


class ProfileStatementsBase:
    """The arrangement every `/auth/me` statements class needs.

    All five usecases behind that path start the same way: resolve the caller's
    account by the id the token carried, or refuse. So the account arrangement,
    the "no such account" case, and the shared 401 assertion live here once.

    The stored password hash is produced by `FakePasswordHasher`, not written as a
    literal, so a test that submits the plaintext is verifying against a hash that
    was actually computed from it.
    """

    FIXED_CLOCK_NOW = datetime(2026, 8, 14, 12, 0, 0, tzinfo=UTC)
    CREATED_AT = datetime(2026, 7, 1, 9, 30, 0, tzinfo=UTC)
    EMAIL = "ada@example.ru"
    PASSWORD = "Str0ng!Pass"
    NAME = "Ada Lovelace"
    # Spelled out rather than imported from profile_errors: importing the constant
    # under test would make the assertion pass for any edit to it.
    UNAUTHORIZED_MESSAGE = "A valid access token is required."
    UNAUTHORIZED_CODE = "UNAUTHORIZED"

    def __init__(self) -> None:
        self.thrown_exception: Exception | None = None
        self.account_repository = FakeAccountRepository()
        self.password_hasher = FakePasswordHasher()
        self.unit_of_work = FakeUnitOfWork()
        self.clock = FakeClock(fixed_now=self.FIXED_CLOCK_NOW)
        self.account: Account | None = None
        self.returned_account: Account | None = None

    @property
    def arranged_account(self) -> Account:
        return arranged(self.account, "account")

    @property
    def account_id(self) -> UUID:
        return self.arranged_account.id

    @property
    def profile(self) -> Account:
        return arranged(self.returned_account, "returned_account")

    async def given_an_account(
        self,
        name: str | None = None,
        avatar_updated_at: datetime | None = None,
        password: str | None = None,
    ) -> None:
        plain_password = self.PASSWORD if password is None else password
        self.account = Account.reconstitute(
            id=uuid4(),
            email=self.EMAIL,
            password_hash=self.password_hasher.hash(plain_password),
            created_at=self.CREATED_AT,
            is_verified=True,
            name=name,
            avatar_updated_at=avatar_updated_at,
        )
        await self.account_repository.save(self.account)

    async def given_an_oauth_account(self, name: str | None = None) -> None:
        """An account created through the OAuth callback: `password_hash=""`.

        The empty string is what is actually stored, not a stand-in for it -- the
        whole password-confirmation guard exists because a naive comparison would
        match it.
        """
        self.account = Account.reconstitute(
            id=uuid4(),
            email=self.EMAIL,
            password_hash="",
            created_at=self.CREATED_AT,
            is_verified=True,
            name=name,
        )
        await self.account_repository.save(self.account)

    def given_no_account_exists_for_the_token_subject(self) -> None:
        """A structurally valid token whose account row is gone."""
        self.account = Account.reconstitute(
            id=uuid4(),
            email=self.EMAIL,
            password_hash="",
            created_at=self.CREATED_AT,
            is_verified=True,
        )
        # Deliberately NOT saved: the id resolves to nothing in the repository.

    async def _capture(self, coroutine):
        try:
            return await coroutine
        except Exception as exc:  # noqa: BLE001 -- every statement asserts afterwards
            self.thrown_exception = exc
            return None

    def assert_refused_as_unauthorized(self) -> None:
        assert isinstance(self.thrown_exception, ValidationException), (
            f"expected a ValidationException, got {self.thrown_exception!r}"
        )
        assert self.thrown_exception.error_code == self.UNAUTHORIZED_CODE
        assert self.thrown_exception.message == self.UNAUTHORIZED_MESSAGE

    def assert_nothing_was_committed(self) -> None:
        assert self.unit_of_work.commit_attempt_count == 0, (
            "expected no commit to have been attempted, got "
            f"{self.unit_of_work.commit_attempt_count}"
        )

    def assert_the_work_was_committed_once(self) -> None:
        assert self.unit_of_work.commit_call_count == 1, (
            f"expected exactly one commit, got {self.unit_of_work.commit_call_count}"
        )
