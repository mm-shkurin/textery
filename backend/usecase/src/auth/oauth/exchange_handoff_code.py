from auth.account_repository import AccountRepository
from auth.handoff_code import MAX_HANDOFF_CODE_LENGTH
from auth.oauth.handoff_code_repository import HandoffCodeRepository
from auth.oauth.oauth_error_codes import INVALID_OR_EXPIRED_OAUTH_CODE
from auth.oauth.rate_limiter import OAuthRateGuard
from auth.token_pair import TokenPair
from auth.token_service import TokenService
from shared.clock import Clock, SystemClock
from shared.exceptions import ValidationException
from shared.unit_of_work import NullUnitOfWork, UnitOfWork


class ExchangeHandoffCode:
    """Leg 3: trade the one-time handoff code for a JWT session.

    The redeem is atomic and single-use, so of two concurrent exchanges of one code
    exactly one mints a session and the other is refused. Every failure answers the
    same `INVALID_OR_EXPIRED_OAUTH_CODE`, so the response never distinguishes an
    unknown code from an expired or already-spent one.
    """

    def __init__(
        self,
        handoff_code_repository: HandoffCodeRepository,
        account_repository: AccountRepository,
        token_service: TokenService,
        clock: Clock | None = None,
        unit_of_work: UnitOfWork | None = None,
        rate_guard: OAuthRateGuard | None = None,
    ) -> None:
        self._handoff_code_repository = handoff_code_repository
        self._account_repository = account_repository
        self._token_service = token_service
        self._clock = clock or SystemClock()
        self._unit_of_work = unit_of_work or NullUnitOfWork()
        self._rate_guard = rate_guard or OAuthRateGuard()

    async def execute(self, code: str, source: str = "") -> TokenPair:
        now = self._clock.now()
        # The abuse bound comes before the code check, so a flood of guesses is
        # throttled on the endpoint rather than each running a store lookup.
        await self._rate_guard.check("exchange", source, now)
        # Bound the length before it reaches the index: an unbounded value is an
        # amplification lever, and no legitimate code approaches this cap.
        if not code or len(code) > MAX_HANDOFF_CODE_LENGTH:
            raise self._invalid()
        account_id = await self._handoff_code_repository.redeem(code, now)
        await self._unit_of_work.commit()
        if account_id is None:
            raise self._invalid()
        account = await self._account_repository.find_by_id(account_id)
        if account is None:
            raise self._invalid()
        return self._token_service.issue_pair(account_id=account.id, email=account.email)

    def _invalid(self) -> ValidationException:
        return ValidationException(
            "the handoff code is unknown, spent or expired", INVALID_OR_EXPIRED_OAUTH_CODE
        )
