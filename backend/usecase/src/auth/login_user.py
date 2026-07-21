import logging
import unicodedata
from uuid import UUID

from auth.account_repository import AccountRepository
from auth.email import Email
from auth.password_hasher import PasswordHasher
from auth.token_pair import TokenPair
from auth.token_service import TokenService
from shared.exceptions import ValidationException
from shared.rollback import rollback_quietly
from shared.unit_of_work import NullUnitOfWork, UnitOfWork

logger = logging.getLogger(__name__)


class LoginUser:
    """Scenario 5.1/5.2/6.1: authenticate an account and issue a token pair."""

    INVALID_CREDENTIALS_MESSAGE = "The email address or password is incorrect."
    UNVERIFIED_MESSAGE = (
        "This account has not been verified yet. Please confirm the code sent to your email."
    )

    def __init__(
        self,
        account_repository: AccountRepository,
        password_hasher: PasswordHasher,
        token_service: TokenService,
        unit_of_work: UnitOfWork | None = None,
    ) -> None:
        self.account_repository = account_repository
        self.password_hasher = password_hasher
        self.token_service = token_service
        # The wrong-password branch increments-then-commits the failed-attempt
        # counter on this UoW (scenario 5.3); NullUnitOfWork is the no-op default
        # for callers that do not supply one.
        self.unit_of_work = unit_of_work or NullUnitOfWork()

    async def execute(self, email: str, password: str) -> TokenPair:
        account = await self.account_repository.find_by_email(self._normalized_email(email))
        if account is None:
            raise self._invalid_credentials()
        if not self.password_hasher.verify(
            self._normalized_password(password), account.password_hash
        ):
            await self._record_failed_attempt(account.id)
            raise self._invalid_credentials()
        # Verified is checked AFTER the password, deliberately. The other order
        # would answer UNVERIFIED to anyone who merely guessed the email, turning
        # a 403 into an account-existence oracle. Answering it only once the
        # password is already proven correct tells the caller nothing they did not
        # know, and 5.1 requires the distinct code so the client can send them to
        # the verify screen instead of showing "wrong password".
        if not account.is_verified:
            raise ValidationException(error_code="UNVERIFIED", message=self.UNVERIFIED_MESSAGE)
        return self.token_service.issue_pair(account_id=account.id, email=account.email)

    async def _record_failed_attempt(self, account_id: UUID) -> None:
        # Increment-then-commit BEFORE the caller raises INVALID_CREDENTIALS, so
        # the count survives the failed login (5.3). Wrapped like VerifyAccount's
        # persist tail: a commit failure (serialization/deadlock/dropped
        # connection) must NOT surface as a 5xx on this previously un-failable read
        # path. Swallow it, roll back the poisoned txn, and let execute() raise the
        # SAME generic INVALID_CREDENTIALS -- the client learns nothing new, and a
        # dropped increment is acceptable next to leaking the real error.
        try:
            await self.account_repository.increment_failed_attempts(account_id)
            await self.unit_of_work.commit()
        except Exception:
            logger.exception("failed to persist the failed-attempt counter")
            await rollback_quietly(self.unit_of_work)

    def _normalized_email(self, email: str) -> str:
        try:
            return Email(email).value
        except ValueError:
            # A malformed email cannot match any stored account, so it takes the
            # same generic path rather than a distinct INVALID_EMAIL. Registration
            # answers INVALID_EMAIL because there is nothing to protect there; at
            # login, a different code for a malformed address would hand out a
            # cheap way to probe which addresses are even considered.
            return ""

    def _normalized_password(self, password: str) -> str:
        # NFC only -- deliberately NOT Password(password).value. The value object
        # also enforces the policy, and a stored credential that predates a policy
        # change must still be able to log in; validating here would lock those
        # accounts out. Normalization itself is required: the hash was computed
        # from the NFC form (scenario 2.7), so a decomposed submission of the same
        # password would not verify without it.
        return unicodedata.normalize("NFC", password)

    def _invalid_credentials(self) -> ValidationException:
        # One error for "no such account" and "wrong password": 5.2 requires them
        # to be indistinguishable, or the response enumerates registered emails.
        return ValidationException(
            error_code="INVALID_CREDENTIALS",
            message=self.INVALID_CREDENTIALS_MESSAGE,
        )
