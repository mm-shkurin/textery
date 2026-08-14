import logging
from uuid import UUID

from auth.account import Account
from auth.account_repository import AccountRepository
from auth.avatar_repository import AvatarRepository
from auth.profile_errors import unauthorized
from shared.rollback import rollback_quietly
from shared.unit_of_work import NullUnitOfWork, UnitOfWork

logger = logging.getLogger(__name__)


class DeleteAvatar:
    """Remove the caller's avatar and answer with the whole profile.

    IDEMPOTENT: deleting an avatar that is not there is a 200, not a 404. The
    client's goal is "the account has no avatar", and that goal is already met --
    reporting a failure would make a retry after a dropped response look like a
    bug to a client that did exactly the right thing. The repository's UPDATE is
    unconditional for the same reason; zero rows changed is success.
    """

    def __init__(
        self,
        account_repository: AccountRepository,
        avatar_repository: AvatarRepository,
        unit_of_work: UnitOfWork | None = None,
    ) -> None:
        self.account_repository = account_repository
        self.avatar_repository = avatar_repository
        self.unit_of_work = unit_of_work or NullUnitOfWork()

    async def execute(self, account_id: UUID) -> Account:
        account = await self.account_repository.find_by_id(account_id)
        if account is None:
            raise unauthorized()
        try:
            await self.avatar_repository.clear_avatar(account_id)
            await self.unit_of_work.commit()
        except Exception:
            logger.exception("failed to clear the avatar")
            await rollback_quietly(self.unit_of_work)
            raise
        # None is the removal: the profile now reports avatar_updated_at=null,
        # which is the same state an account that never had an avatar is in.
        account.set_avatar_updated_at(None)
        return account
