from uuid import UUID

from auth.avatar_repository import AvatarRepository, StoredAvatar
from shared.exceptions import NotFoundException


class GetAvatar:
    """The caller's own avatar image.

    Takes an account id and nothing else -- the id comes from the token, never
    from the path -- so this route cannot be pointed at anyone else's image and
    has no ownership check to get wrong.

    Raises NotFoundException when there is no avatar, which the existing handler
    renders as a 404 in the canonical envelope. That is the only failure this
    usecase has: an account that does not exist was already refused with 401 by
    the auth dependency before this runs.
    """

    def __init__(self, avatar_repository: AvatarRepository) -> None:
        self._avatar_repository = avatar_repository

    async def execute(self, account_id: UUID) -> StoredAvatar:
        avatar = await self._avatar_repository.find_avatar(account_id)
        if avatar is None:
            raise NotFoundException(f"account {account_id} has no avatar")
        return avatar
