from datetime import UTC, datetime
from uuid import uuid4

from auth.account import Account
from auth.refresh_access_token import RefreshAccessToken
from auth.token_pair import TokenPair
from fake.auth.fake_account_repository import FakeAccountRepository
from fake.auth.fake_password_hasher import FakePasswordHasher
from fake.auth.fake_token_service import FakeTokenService
from shared.exceptions import InvalidTokenException, ValidationException
from statements.arranged import arranged


class RefreshStatements:
    """Scenarios 6.2 and 6.3: exchanging a refresh token for a fresh pair."""

    FIXED_NOW = datetime(2026, 7, 16, 12, 0, 0, tzinfo=UTC)
    SUBMITTED_TOKEN = "some-refresh-token"
    # Spelled out rather than imported from RefreshAccessToken -- importing the
    # constant under test would make the assertion pass for any edit to it.
    INVALID_REFRESH_MESSAGE = "The refresh token is invalid or has expired."

    def __init__(self) -> None:
        self.thrown_exception: Exception | None = None
        self.account_repository = FakeAccountRepository()
        self.password_hasher = FakePasswordHasher()
        self.token_service = FakeTokenService()
        self.account: Account | None = None
        self.issued_pair: TokenPair | None = None

    @property
    def registered_account(self) -> Account:
        """The account a `given_*` step saved -- required by every assert step."""
        return arranged(self.account, "account")

    async def _given_account(self, is_verified: bool) -> Account:
        account = Account.reconstitute(
            id=uuid4(),
            email="user@example.ru",
            password_hash=self.password_hasher.hash("Str0ng!Pass"),
            created_at=self.FIXED_NOW,
            is_verified=is_verified,
        )
        await self.account_repository.save(account)
        self.account = account
        return account

    async def given_a_refresh_token_for_a_verified_account(self) -> None:
        account = await self._given_account(is_verified=True)
        self.token_service.refresh_subject = account.id

    async def given_a_refresh_token_for_an_account_that_since_became_unverified(self) -> None:
        # A token outlives the state it was minted from. The account was verified
        # when the token was issued and is not any more.
        account = await self._given_account(is_verified=False)
        self.token_service.refresh_subject = account.id

    async def given_a_refresh_token_for_an_account_that_no_longer_exists(self) -> None:
        # Nothing saved: the token names an account id the repository cannot find,
        # which is what a deleted account looks like from here.
        self.token_service.refresh_subject = uuid4()

    async def given_a_token_the_token_service_rejects(self) -> None:
        # Stands for every cause at once -- expired, forged, signed by a rotated
        # key, or an access token submitted at /refresh. The port collapses them
        # into one exception on purpose, so the usecase has exactly one branch.
        await self._given_account(is_verified=True)
        self.token_service.raise_on_read_refresh_subject = InvalidTokenException(
            "refresh token is not valid"
        )

    async def submit_the_refresh_token(self) -> None:
        try:
            self.issued_pair = await RefreshAccessToken(
                account_repository=self.account_repository,
                token_service=self.token_service,
            ).execute(refresh_token=self.SUBMITTED_TOKEN)
        except Exception as exc:
            self.thrown_exception = exc

    def assert_fresh_token_pair_issued_for_the_account(self) -> None:
        assert self.thrown_exception is None, (
            f"expected no exception on a valid refresh, got "
            f"{type(self.thrown_exception).__name__}: {self.thrown_exception}"
        )
        assert self.token_service.issued_for == [
            (self.registered_account.id, self.registered_account.email)
        ], (
            f"expected exactly one pair issued for "
            f"{(self.registered_account.id, self.registered_account.email)}, "
            f"got {self.token_service.issued_for}"
        )
        expected_pair = FakeTokenService().issue_pair(
            account_id=self.registered_account.id, email=self.registered_account.email
        )
        assert self.issued_pair == expected_pair, (
            f"expected the usecase to return the pair the token service minted "
            f"({expected_pair}), got {self.issued_pair}"
        )

    def assert_rejected_as_invalid_refresh_token(self) -> None:
        """One generic rejection, and no fresh token minted.

        Expired, forged, unknown-account and unverified-account all answer
        identically: anything more specific tells an attacker which of their
        guesses was closer.
        """
        assert isinstance(self.thrown_exception, ValidationException), (
            f"expected ValidationException('INVALID_REFRESH_TOKEN'), got "
            f"{type(self.thrown_exception).__name__ if self.thrown_exception else None}: "
            f"{self.thrown_exception}"
        )
        actual = (self.thrown_exception.error_code, self.thrown_exception.message)
        expected = ("INVALID_REFRESH_TOKEN", self.INVALID_REFRESH_MESSAGE)
        assert actual == expected, f"expected {expected}, got {actual}"
        assert self.token_service.issued_for == [], (
            f"expected no token pair to be issued on a rejected refresh, "
            f"got {self.token_service.issued_for}"
        )
