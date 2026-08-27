import logging

from analytics.analytics_recorder import AnalyticsRecorder, NullAnalyticsRecorder, occurrence_of
from analytics.event_names import REGISTRATION_COMPLETED
from auth.account import Account
from auth.account_repository import AccountRepository
from auth.account_verification_deps import AccountVerificationDependencies
from auth.email_validation import validate_email
from auth.verification_code import VerificationCode
from auth.verification_code_repository import VerificationCodeRepository
from auth.verification_code_value import VerificationCodeValue
from shared.clock import Clock
from shared.error_codes import ErrorCode
from shared.exceptions import ValidationException, VerificationFailedException
from shared.rollback import rollback_quietly
from shared.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)

# Why `execute` reads in the order it does.
#
# Both shape checks run BEFORE any repository lookup, so a malformed request costs
# zero queries. Email is validated first: a request bad on both axes answers
# INVALID_EMAIL, matching `RegisterUser`'s order.
#
# The registration event is emitted AFTER the transition is committed, and only on
# the path that actually performed it. The already-verified branch returns before
# reaching it, so confirming the same code twice records ONE registration (§8.2) --
# and the derived occurrence key collapses two that race each other into one row
# as well (§8.3).


class VerifyAccount(AccountVerificationDependencies):
    VERIFICATION_FAILED_MESSAGE = (
        "Verification could not be completed due to an unexpected error. Please try again."
    )

    def __init__(
        self,
        account_repository: AccountRepository,
        verification_code_repository: VerificationCodeRepository,
        clock: Clock,
        unit_of_work: UnitOfWork | None = None,
        analytics_recorder: AnalyticsRecorder | None = None,
    ) -> None:
        """The four shared ports, plus a fifth this usecase alone has.

        The recorder is NOT on `AccountVerificationDependencies`: `ResendCode`
        holds the same four collaborators and emits nothing, and widening the
        shared base would hand it a dependency it has no use for. One extra
        constructor here is cheaper than a port nobody in the other usecase calls.
        """
        super().__init__(account_repository, verification_code_repository, clock, unit_of_work)
        self._analytics_recorder = analytics_recorder or NullAnalyticsRecorder()

    async def execute(self, email: str, code: str) -> None:
        """Confirm the code. Why it reads in this order: the note above the class."""
        normalized_email = validate_email(email).value
        self._validate_code(code)
        account = await self._account_repository.find_by_email(normalized_email)
        if account is None:
            raise self._invalid_or_expired()
        verification_code = await self._verification_code_repository.find_active_by_account_id(
            account.id
        )
        if verification_code is None:
            raise self._invalid_or_expired()

        if account.is_verified:
            self._settle_an_already_verified_account(verification_code, code)
            return

        self._refuse_unless_usable(verification_code, code)
        await self._apply_verification(account, verification_code)
        await self._analytics_recorder.record(
            event_name=REGISTRATION_COMPLETED,
            visitor_id=None,
            user_id=account.id,
            occurrence_key=occurrence_of(REGISTRATION_COMPLETED, account.id),
        )

    def _settle_an_already_verified_account(
        self, verification_code: VerificationCode, code: str
    ) -> None:
        """The transition already happened, so it must not happen a second time.

        Returning rather than running the consume/save/commit tail again is what
        makes a re-clicked link idempotent (scenario 3.4). Checked BEFORE expiry
        on purpose: re-clicking with the same code after the TTL is still
        idempotent success, not a 400.
        """
        if not verification_code.matches(code):
            raise self._already_verified()

    def _refuse_unless_usable(self, verification_code: VerificationCode, code: str) -> None:
        """Wrong code and expired code answer identically -- neither confirms the other."""
        if not verification_code.matches(code):
            raise self._invalid_or_expired()
        if self._clock.now() >= verification_code.expires_at:
            raise self._invalid_or_expired()

    async def _apply_verification(
        self, account: Account, verification_code: VerificationCode
    ) -> None:
        # Persist via the atomic conditional-UPDATE port methods, not the
        # lock-free verify()+save() / consume()+save() pair: the DB does the
        # single-row transition so exactly one concurrent verify wins (the loser
        # resolves to idempotent success — both True/False are success here, no
        # branch needed). The commit stays: the atomic methods carry no internal
        # commit (caller owns the txn).
        #
        # Latent-divergence note: unlike the Fakes, production's bulk UPDATE does
        # NOT mutate the in-memory account/verification_code. Nothing downstream
        # of this call reads is_verified/consumed_at in the same txn today. A
        # future verify side-effect (welcome email/token/credit) must re-read the
        # rows or synchronize_session rather than trust these stale in-memory
        # objects.
        try:
            await self._account_repository.transition_to_verified(account.id)
            await self._verification_code_repository.transition_to_consumed(
                verification_code.id, self._clock.now()
            )
            await self._unit_of_work.commit()
        except Exception as error:
            # See RegisterUser: the client's answer is deliberately vague, so the
            # real cause has to be logged here or it is lost entirely.
            logger.exception("verification failed while persisting the verified account")
            await rollback_quietly(self._unit_of_work)
            raise VerificationFailedException(message=self.VERIFICATION_FAILED_MESSAGE) from error

    def _validate_code(self, code: str) -> VerificationCodeValue:
        try:
            return VerificationCodeValue(code)
        except ValueError as error:
            raise ValidationException(
                error_code=ErrorCode.INVALID_CODE,
                message="The verification code is not valid.",
            ) from error
