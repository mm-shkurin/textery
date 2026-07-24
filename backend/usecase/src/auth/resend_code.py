import logging
from datetime import timedelta
from uuid import uuid4

from auth.account_repository import AccountRepository
from auth.email_validation import validate_email
from auth.verification_code import VerificationCode
from auth.verification_code_repository import VerificationCodeRepository
from shared.clock import Clock
from shared.exceptions import ValidationException
from shared.rollback import rollback_quietly
from shared.unit_of_work import NullUnitOfWork, UnitOfWork

logger = logging.getLogger(__name__)

_COOLDOWN = timedelta(seconds=60)


class ResendCode:
    """Resend a verification code for a pending account (scenario 4.x).

    A NEW top-level usecase, not a method on VerifyAccount: resend is a distinct
    register-like issuance gated by a cooldown, so per the usecase-interaction rule
    it is its own entry point, sharing only domain-level code generation with
    registration. Reuses the same ports RegisterUser/VerifyAccount depend on
    (AccountRepository, VerificationCodeRepository, Clock, UnitOfWork).
    """

    COOLDOWN_MESSAGE = (
        "A verification code was recently sent. Please wait before requesting another."
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

    async def execute(self, email: str) -> VerificationCode:
        normalized_email = validate_email(email).value
        account = await self.account_repository.find_by_email(normalized_email)
        if account is None:
            # No account-existence oracle: an unknown email answers with the same
            # generic rejection the verify path uses, per the resend ADR.
            raise self._invalid_or_expired()

        # Re-read the account under SELECT ... FOR UPDATE so the db serialization
        # proven by the db-adapter race test is exercised in production (scenario 4.4).
        # Acquired AFTER resolving the id via find_by_email and BEFORE the cooldown
        # read, and threaded forward so ALL downstream work uses the LOCKED row.
        account = await self.account_repository.lock_for_update(account.id)
        if account is None:
            # Defensive (premortem REMOTE): no delete path exists today, but if the row
            # vanished between find_by_email and the lock, answer with the same rejection.
            raise self._invalid_or_expired()

        if account.is_verified:
            # Gate on the POST-lock account (lock_for_update's re-read), BEFORE the
            # cooldown read: a verified account answers ALREADY_VERIFIED (3.5's 409
            # taxonomy), never RESEND_COOLDOWN_ACTIVE, and issues no new code. Placed
            # here so a verify that committed inside the lock window is still caught
            # (scenario 4.5).
            raise self._already_verified()

        newest = await self.verification_code_repository.find_active_by_account_id(account.id)
        if newest is not None:
            self._enforce_cooldown(newest)

        return await self._issue_new_code(account.id)

    def _enforce_cooldown(self, newest: VerificationCode) -> None:
        # Cooldown is measured from the NEWEST code's created_at (max(created_at)),
        # including the registration code, so a just-registered account cannot
        # resend immediately (abuse vector). Allowed when now - created_at >= 60s.
        if self.clock.now() - newest.created_at < _COOLDOWN:
            raise ValidationException(
                error_code="RESEND_COOLDOWN_ACTIVE",
                message=self.COOLDOWN_MESSAGE,
            )

    async def _issue_new_code(self, account_id) -> VerificationCode:
        # Insert-only supersession: a fresh code is persisted, no old row deleted or
        # mutated. find_active_by_account_id returns most-recent-wins, so the old
        # code stops verifying. A legal resend is always >=60s later, giving the new
        # code a strictly-greater created_at than the superseded one.
        verification_code = VerificationCode.generate(
            id=uuid4(),
            account_id=account_id,
            created_at=self.clock.now(),
        )
        try:
            await self.verification_code_repository.save(verification_code)
            await self.unit_of_work.commit()
        except Exception:
            logger.exception("resend failed while saving the verification code")
            await rollback_quietly(self.unit_of_work)
            raise
        return verification_code

    def _already_verified(self) -> ValidationException:
        # Mirrors VerifyAccount._already_verified (scenario 3.5): the account has
        # already transitioned, so a resend is a genuine 409 conflict, not the
        # generic state-hiding rejection.
        return ValidationException(
            error_code="ALREADY_VERIFIED",
            message="The account is already verified.",
        )

    def _invalid_or_expired(self) -> ValidationException:
        return ValidationException(
            error_code="INVALID_OR_EXPIRED_CODE",
            message="The verification code is invalid or has expired.",
        )
