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

    async def execute(self, email: str) -> None:
        normalized_email = validate_email(email).value
        account = await self.account_repository.find_by_email(normalized_email)
        if account is None:
            # No account-existence oracle: an unknown email answers with the same
            # generic rejection the verify path uses, per the resend ADR.
            raise self._invalid_or_expired()

        newest = await self.verification_code_repository.find_active_by_account_id(account.id)
        if newest is not None:
            self._enforce_cooldown(newest)

        await self._issue_new_code(account.id)

    def _enforce_cooldown(self, newest: VerificationCode) -> None:
        # Cooldown is measured from the NEWEST code's created_at (max(created_at)),
        # including the registration code, so a just-registered account cannot
        # resend immediately (abuse vector). Allowed when now - created_at >= 60s.
        if self.clock.now() - newest.created_at < _COOLDOWN:
            raise ValidationException(
                error_code="RESEND_COOLDOWN_ACTIVE",
                message=self.COOLDOWN_MESSAGE,
            )

    async def _issue_new_code(self, account_id) -> None:
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
        except Exception as error:
            logger.exception("resend failed while saving the verification code")
            await rollback_quietly(self.unit_of_work)
            raise

    def _invalid_or_expired(self) -> ValidationException:
        return ValidationException(
            error_code="INVALID_OR_EXPIRED_CODE",
            message="The verification code is invalid or has expired.",
        )
