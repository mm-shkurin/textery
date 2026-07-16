from auth.account_repository import AccountRepository
from auth.token_pair import TokenPair
from auth.token_service import TokenService
from shared.exceptions import InvalidTokenException, ValidationException


class RefreshAccessToken:
    """Scenario 6.2/6.3: exchange a valid refresh token for a fresh token pair."""

    INVALID_REFRESH_MESSAGE = "The refresh token is invalid or has expired."

    def __init__(
        self,
        account_repository: AccountRepository,
        token_service: TokenService,
    ) -> None:
        self.account_repository = account_repository
        self.token_service = token_service

    async def execute(self, refresh_token: str) -> TokenPair:
        try:
            account_id = self.token_service.read_refresh_subject(refresh_token)
        except InvalidTokenException:
            raise self._invalid_refresh()
        account = await self.account_repository.find_by_id(account_id)
        # The account is re-read rather than trusted from the claims: a token
        # outlives the state it was minted from, so a deleted or un-verified
        # account must stop refreshing instead of riding a 7-day token.
        if account is None or not account.is_verified:
            raise self._invalid_refresh()
        return self.token_service.issue_pair(account_id=account.id, email=account.email)

    def _invalid_refresh(self) -> ValidationException:
        # One answer for expired, forged, wrong-type, and unknown-account alike --
        # anything more specific tells an attacker which of their guesses was
        # closer.
        return ValidationException(
            error_code="INVALID_REFRESH_TOKEN",
            message=self.INVALID_REFRESH_MESSAGE,
        )
