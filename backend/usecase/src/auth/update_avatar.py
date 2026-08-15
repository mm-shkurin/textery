import logging
from uuid import UUID

from auth.account import Account
from auth.account_repository import AccountRepository
from auth.avatar import Avatar
from auth.avatar_repository import AvatarRepository
from auth.profile_errors import unauthorized
from shared.clock import Clock, SystemClock
from shared.rollback import rollback_quietly
from shared.unit_of_work import NullUnitOfWork, UnitOfWork

logger = logging.getLogger(__name__)


class UpdateAvatar:
    """Store an uploaded image and answer with the caller's whole profile.

    The full profile, not just the new timestamp: the client replaces its identity
    snapshot from this response, exactly as it does after a rename, so there is no
    follow-up `GET /me` on the highest-rate endpoint after every upload.

    The bytes are stored EXACTLY as received. No decode, no re-encode, no resize,
    no metadata stripping -- the client uploads an already-scaled image, and every
    one of those operations would mean putting an image decoder in the path of
    untrusted input on an authenticated route.
    """

    def __init__(
        self,
        account_repository: AccountRepository,
        avatar_repository: AvatarRepository,
        clock: Clock | None = None,
        unit_of_work: UnitOfWork | None = None,
    ) -> None:
        self.account_repository = account_repository
        self.avatar_repository = avatar_repository
        self.clock = clock or SystemClock()
        # A real UnitOfWork on the repository's own session is required in
        # production: NullUnitOfWork.commit() is a silent no-op, so a mis-wired
        # usecase answers 200 with a fresh avatar_updated_at and stores nothing.
        self.unit_of_work = unit_of_work or NullUnitOfWork()

    async def execute(self, account_id: UUID, data: bytes) -> Account:
        # Validated BEFORE anything is read or written, so a refused upload costs
        # zero queries and never reaches storage. This is also what makes the
        # "nothing was saved" half of the refusal contract true by construction
        # rather than by a rollback.
        avatar = Avatar(data)
        account = await self.account_repository.find_by_id(account_id)
        if account is None:
            raise unauthorized()
        updated_at = self.clock.now()
        try:
            await self.avatar_repository.update_avatar(
                account_id=account_id,
                data=avatar.data,
                # The type the DOMAIN read out of the magic bytes. The client's
                # Content-Type never reaches storage, and therefore never reaches
                # the response this image is served with.
                media_type=avatar.media_type,
                updated_at=updated_at,
            )
            await self.unit_of_work.commit()
        except Exception:
            logger.exception("failed to persist the uploaded avatar")
            await rollback_quietly(self.unit_of_work)
            raise
        # The entity was read before the UPDATE and still carries the old
        # timestamp; applying it here is what makes the returned profile the state
        # the client should now hold, without a second SELECT for a value this
        # process just chose.
        account.set_avatar_updated_at(updated_at)
        return account
