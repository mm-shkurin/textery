import unicodedata
from datetime import UTC, datetime
from uuid import uuid4

from scope.register_request_scope import RegisterRequestScope

from auth.account import Account
from auth.login_user import LoginUser
from auth.register_user import RegisterUser
from auth.verify_account import VerifyAccount
from fake.auth.fake_account_repository import FakeAccountRepository
from fake.auth.fake_clock import FakeClock
from fake.auth.fake_password_hasher import FakePasswordHasher
from fake.auth.fake_token_service import FakeTokenService
from fake.auth.fake_unit_of_work import FakeUnitOfWork
from fake.auth.fake_verification_code_repository import FakeVerificationCodeRepository
from shared.exceptions import ValidationException


class LoginStatements:
    """Scenarios 5.1, 5.2 and 6.1: authenticating an account and issuing tokens."""

    FIXED_CLOCK_NOW = datetime(2026, 7, 16, 12, 0, 0, tzinfo=UTC)
    WRONG_PASSWORD = "Wr0ng!Pass"
    UNKNOWN_EMAIL = "nobody@example.ru"
    MALFORMED_EMAIL = "not-an-email"
    # Precomposed "é" (U+00E9). The decomposed twin below is the same password to
    # a human and a different byte string to a hasher.
    ACCENTED_PASSWORD_NFC = unicodedata.normalize("NFC", "Str0ng!Passé")
    ACCENTED_PASSWORD_NFD = unicodedata.normalize("NFD", "Str0ng!Passé")
    # Fails today's policy (too short, no digit/upper/special). Stands for a
    # credential stored before the policy tightened.
    LEGACY_WEAK_PASSWORD = "weakpw"
    # Spelled out rather than imported from LoginUser -- importing the constant it
    # pins would make the assertion pass for any edit to it.
    INVALID_CREDENTIALS_MESSAGE = "The email address or password is incorrect."
    UNVERIFIED_MESSAGE = (
        "This account has not been verified yet. Please confirm the code sent to your email."
    )

    def __init__(self) -> None:
        self.thrown_exception: Exception | None = None
        self.account_repository = FakeAccountRepository()
        self.password_hasher = FakePasswordHasher()
        self.token_service = FakeTokenService()
        self.clock = FakeClock(fixed_now=self.FIXED_CLOCK_NOW)
        self.verification_code_repository = FakeVerificationCodeRepository()
        self.unit_of_work = FakeUnitOfWork()
        self.account_email: str | None = None
        self.account_password: str | None = None
        self.account_id = None
        self.issued_pair = None

    async def _register(self, password: str) -> None:
        scope = RegisterRequestScope.builder(password=password, confirm_password=password)
        result = await RegisterUser(
            password_hasher=self.password_hasher,
            account_repository=self.account_repository,
            clock=self.clock,
            verification_code_repository=self.verification_code_repository,
        ).execute(
            email=scope.email,
            password=scope.password,
            confirm_password=scope.confirm_password,
        )
        self.account_email = result.account.email
        self.account_id = result.account.id
        self.account_password = password
        self.issued_code = result.verification_code.code

    async def _verify(self) -> None:
        await VerifyAccount(
            account_repository=self.account_repository,
            verification_code_repository=self.verification_code_repository,
            clock=self.clock,
            unit_of_work=self.unit_of_work,
        ).execute(email=self.account_email, code=self.issued_code)

    async def given_verified_account(self) -> None:
        await self._register(RegisterRequestScope.DEFAULTS["password"])
        await self._verify()

    async def given_pending_account(self) -> None:
        await self._register(RegisterRequestScope.DEFAULTS["password"])

    async def given_verified_account_registered_with_a_precomposed_password(self) -> None:
        await self._register(self.ACCENTED_PASSWORD_NFC)
        await self._verify()

    async def given_verified_account_whose_password_predates_the_policy(self) -> None:
        # Built directly, not through RegisterUser: today's Password value object
        # would reject this password outright, which is the whole point -- the
        # stored hash was computed when the rule was looser.
        account = Account.reconstitute(
            id=uuid4(),
            email="legacy@example.ru",
            password_hash=self.password_hasher.hash(self.LEGACY_WEAK_PASSWORD),
            created_at=self.FIXED_CLOCK_NOW,
            is_verified=True,
        )
        await self.account_repository.save(account)
        self.account_email = account.email
        self.account_id = account.id
        self.account_password = self.LEGACY_WEAK_PASSWORD

    async def _execute_login(self, email: str, password: str) -> None:
        try:
            self.issued_pair = await LoginUser(
                account_repository=self.account_repository,
                password_hasher=self.password_hasher,
                token_service=self.token_service,
            ).execute(email=email, password=password)
        except Exception as exc:
            self.thrown_exception = exc

    async def login_with_the_correct_password(self) -> None:
        await self._execute_login(self.account_email, self.account_password)

    async def login_with_a_wrong_password(self) -> None:
        await self._execute_login(self.account_email, self.WRONG_PASSWORD)

    async def login_with_an_unknown_email(self) -> None:
        await self._execute_login(self.UNKNOWN_EMAIL, RegisterRequestScope.DEFAULTS["password"])

    async def login_with_a_malformed_email(self) -> None:
        await self._execute_login(self.MALFORMED_EMAIL, RegisterRequestScope.DEFAULTS["password"])

    async def login_with_the_email_in_a_different_case(self) -> None:
        await self._execute_login(self.account_email.upper(), self.account_password)

    async def login_with_the_decomposed_form_of_the_password(self) -> None:
        await self._execute_login(self.account_email, self.ACCENTED_PASSWORD_NFD)

    def assert_token_pair_issued_for_the_account(self) -> None:
        assert self.thrown_exception is None, (
            f"expected no exception on a valid login, got "
            f"{type(self.thrown_exception).__name__}: {self.thrown_exception}"
        )
        assert self.token_service.issued_for == [(self.account_id, self.account_email)], (
            f"expected exactly one pair issued for {(self.account_id, self.account_email)}, "
            f"got {self.token_service.issued_for}"
        )
        expected_pair = FakeTokenService().issue_pair(
            account_id=self.account_id, email=self.account_email
        )
        assert self.issued_pair == expected_pair, (
            f"expected the usecase to return the pair the token service minted "
            f"({expected_pair}), got {self.issued_pair}"
        )

    def _assert_validation_exception(self, expected_error_code: str, expected_message: str) -> None:
        assert isinstance(self.thrown_exception, ValidationException), (
            f"expected ValidationException('{expected_error_code}'), got "
            f"{type(self.thrown_exception).__name__ if self.thrown_exception else None}: "
            f"{self.thrown_exception}"
        )
        actual = (self.thrown_exception.error_code, self.thrown_exception.message)
        expected = (expected_error_code, expected_message)
        assert actual == expected, f"expected {expected}, got {actual}"

    def assert_rejected_as_invalid_credentials(self) -> None:
        """One generic rejection, and no token minted.

        The sameness across "no such account", "wrong password" and "malformed
        email" is the requirement (5.2): any distinction turns the response into
        an oracle for which emails are registered.
        """
        self._assert_validation_exception("INVALID_CREDENTIALS", self.INVALID_CREDENTIALS_MESSAGE)
        assert self.token_service.issued_for == [], (
            f"expected no token pair to be issued on a rejected login, "
            f"got {self.token_service.issued_for}"
        )

    def assert_rejected_as_unverified(self) -> None:
        self._assert_validation_exception("UNVERIFIED", self.UNVERIFIED_MESSAGE)
        assert self.token_service.issued_for == [], (
            f"expected no token pair to be issued for an unverified account, "
            f"got {self.token_service.issued_for}"
        )
