from auth.account_repository import AccountRepository
from auth.handoff_code import MAX_HANDOFF_CODE_LENGTH
from auth.oauth.handoff_code_repository import HandoffCodeRepository
from auth.oauth.oauth_error_codes import INVALID_OR_EXPIRED_OAUTH_CODE
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
    ) -> None:
        self._handoff_code_repository = handoff_code_repository
        self._account_repository = account_repository
        self._token_service = token_service
        self._clock = clock or SystemClock()
        self._unit_of_work = unit_of_work or NullUnitOfWork()

    async def execute(self, code: str) -> TokenPair:
        # Bound the length before it reaches the index: an unbounded value is an
        # amplification lever, and no legitimate code approaches this cap.
        if not code or len(code) > MAX_HANDOFF_CODE_LENGTH:
            raise self._invalid()
        account_id = await self._handoff_code_repository.redeem(code, self._clock.now())
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
