import logging

from auth.account import Account
from auth.account_repository import AccountRepository
from auth.email_validation import validate_email
from auth.verification_code import VerificationCode
from auth.verification_code_repository import VerificationCodeRepository
from auth.verification_code_value import VerificationCodeValue
from shared.clock import Clock
from shared.exceptions import ValidationException, VerificationFailedException
from shared.rollback import rollback_quietly
from shared.unit_of_work import NullUnitOfWork, UnitOfWork

logger = logging.getLogger(__name__)


class VerifyAccount:
    VERIFICATION_FAILED_MESSAGE = (
        "Verification could not be completed due to an unexpected error. Please try again."
    )

    def __init__(
        self,
        account_repository: AccountRepository,
        verification_code_repository: VerificationCodeRepository,
        clock: Clock,
        unit_of_work: UnitOfWork | None = None,
    ) -> None:
        self.account_repository = account_repository
        self.verification_code_repository = verification_code_repository
        self.clock = clock
        self.unit_of_work = unit_of_work or NullUnitOfWork()

    async def execute(self, email: str, code: str) -> None:
        # Both shape checks run before any repository lookup, so a malformed
        # request costs zero queries. Email is validated first: a request bad on
        # both axes answers INVALID_EMAIL, matching RegisterUser's order.
        normalized_email = validate_email(email).value
        self._validate_code(code)
        account = await self.account_repository.find_by_email(normalized_email)
        if account is None:
            raise self._invalid_or_expired()
        verification_code = await self.verification_code_repository.find_active_by_account_id(
            account.id
        )
        if verification_code is None:
            raise self._invalid_or_expired()

        if account.is_verified:
            # Already verified: the transition already happened. Do NOT run the
            # consume/save/commit tail again (no duplicate state transition,
            # scenario 3.4). This sits BEFORE the expiry check on purpose:
            # re-clicking the verify link with the same code after the TTL is
            # still idempotent success, not a 400.
            if verification_code.matches(code):
                return
            raise self._already_verified()

        if not verification_code.matches(code):
            raise self._invalid_or_expired()
        if self.clock.now() >= verification_code.expires_at:
            raise self._invalid_or_expired()

        await self._apply_verification(account, verification_code)

    async def _apply_verification(
        self, account: Account, verification_code: VerificationCode
    ) -> None:
        account.verify()
        verification_code.consume(consumed_at=self.clock.now())
        try:
            await self.account_repository.save(account)
            await self.verification_code_repository.save(verification_code)
            await self.unit_of_work.commit()
        except Exception as error:
            # See RegisterUser: the client's answer is deliberately vague, so the
            # real cause has to be logged here or it is lost entirely.
            logger.exception("verification failed while persisting the verified account")
            await rollback_quietly(self.unit_of_work)
            raise VerificationFailedException(message=self.VERIFICATION_FAILED_MESSAGE) from error

    def _validate_code(self, code: str) -> VerificationCodeValue:
        try:
            return VerificationCodeValue(code)
        except ValueError as error:
            raise ValidationException(
                error_code="INVALID_CODE",
                message="The verification code is not valid.",
            ) from error

    def _already_verified(self) -> ValidationException:
        """The account is already verified and a NON-matching code was submitted.

        Distinct from _invalid_or_expired: on an already-verified account the
        transition is done, so a code that is not the one that verified it is a
        genuine conflict, not a state-hiding oracle. The matching code takes the
        idempotent-success path above and never reaches here.
        """
        return ValidationException(
            error_code="ALREADY_VERIFIED",
            message="The account is already verified.",
        )

    def _invalid_or_expired(self) -> ValidationException:
        """One generic rejection for every failure that depends on stored state.

        Wrong code, no such account, and no issued code all answer identically, on
        purpose: auth_verify.yaml requires the 400 to be client-safe and to not
        reveal whether the email exists. Giving the unknown-account case its own
        code (or letting it 500 on a None dereference, which is what happened
        before this) turns the status line into an account-existence oracle.

        Distinct from INVALID_CODE, which is shape-only: that one is a pure
        function of the submitted string and reveals nothing about any account.

        Known gap, not closed here: the unknown-account branch returns after one
        query while a wrong code costs two, so the paths are still
        distinguishable by timing. Out of scope for this sprint.
        """
        return ValidationException(
            error_code="INVALID_OR_EXPIRED_CODE",
            message="The verification code is invalid or has expired.",
        )
