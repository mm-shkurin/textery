from uuid import UUID

from auth.account import Account
from auth.account_repository import AccountRepository
from auth.profile_errors import unauthorized


class GetProfile:
    """The caller's own profile, resolved from the token subject.

    Takes an account id and nothing else. There is no lookup by email, no filter,
    and no widening parameter -- the read is scoped to the caller by construction,
    which is why `GET /api/v1/auth/me` has no 404 to answer: it accepts no
    identifier, so there is nothing to enumerate.
    """

    def __init__(self, account_repository: AccountRepository) -> None:
        self._account_repository = account_repository

    async def execute(self, account_id: UUID) -> Account:
        account = await self._account_repository.find_by_id(account_id)
        if account is None:
            # A structurally valid token whose account row is gone answers exactly
            # as a forged one does -- 401, never 404. Distinguishing them tells the
            # holder of a token that it was well-formed, and nothing the client can
            # do about either case differs.
            raise unauthorized()
        return account
