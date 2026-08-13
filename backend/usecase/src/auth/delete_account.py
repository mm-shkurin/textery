import logging
from uuid import UUID

from auth.account_eraser import AccountEraser
from auth.account_repository import AccountRepository
from auth.deletion_confirmation import (
    confirmation_invalid,
    email_confirms,
    has_password,
    password_confirms,
)
from auth.password_hasher import PasswordHasher
from auth.profile_errors import unauthorized
from shared.rollback import rollback_quietly
from shared.unit_of_work import NullUnitOfWork, UnitOfWork

logger = logging.getLogger(__name__)


class DeleteAccount:
    """Delete the caller's own account and everything belonging to it. Irreversibly.

    THE ONLY IRREVERSIBLE OPERATION IN THE PRODUCT. There is no soft delete, no
    grace period and no recycle bin -- that is a decision, not an omission, and it
    is why this usecase confirms before it acts and does the whole removal inside
    ONE transaction. A partial deletion is the worst outcome available: an account
    whose documents are gone, or documents belonging to an account that is not
    there.

    **The confirmation branch is chosen by the ACCOUNT, never by the request.**
    An account with a password can only be confirmed by that password; an
    OAuth-only account (stored `password_hash=""`) can only be confirmed by
    retyping its own address. Letting the client pick would mean an account with a
    password could be deleted by someone who merely read the email off the screen
    -- which the deletion screen displays.

    **No migration adds `ON DELETE CASCADE`.** Three of the child tables reference
    `accounts.id` with NO ACTION and `documents.owner_id` has no foreign key at
    all, so the removal is explicit in `SqlAlchemyAccountEraser`. Altering
    constraints on three tables of a populated database -- and validating every
    existing `documents` row before it could take a foreign key -- is a data-repair
    job of its own. The absence of that migration is deliberate; see the eraser's
    docstring for the full order and its reasons.

    **Nothing is done about the caller's still-valid access token, on purpose.**
    It stays cryptographically valid for up to fifteen minutes, but
    `get_current_owner_id` confirms the account row exists on every authenticated
    request, so the very next call from any tab or device answers 401 --
    indistinguishable from a forged token. The deletion is therefore effective
    immediately everywhere, with no revocation list to build.
    """

    def __init__(
        self,
        account_repository: AccountRepository,
        account_eraser: AccountEraser,
        password_hasher: PasswordHasher,
        unit_of_work: UnitOfWork | None = None,
    ) -> None:
        self.account_repository = account_repository
        self.account_eraser = account_eraser
        self.password_hasher = password_hasher
        # A real UnitOfWork bound to the eraser's own session is not optional
        # here. NullUnitOfWork.commit() is a silent no-op, so a mis-wired usecase
        # would answer 204 while the session rolled every DELETE back on close --
        # "your account is gone" over an account that is still there.
        self.unit_of_work = unit_of_work or NullUnitOfWork()

    async def execute(
        self, account_id: UUID, password: object = None, confirm_email: object = None
    ) -> None:
        account = await self.account_repository.find_by_id(account_id)
        if account is None:
            # The token resolved but the row is gone -- already deleted, or deleted
            # by a racing request. Same 401 the auth boundary gives a forgery.
            raise unauthorized()
        if not self._confirmed(account, password, confirm_email):
            # Raised BEFORE the eraser is constructed into the call, so "nothing
            # was deleted on a refusal" is true by control flow rather than by a
            # rollback that has to work.
            raise confirmation_invalid()
        try:
            await self.account_eraser.erase(account_id)
            await self.unit_of_work.commit()
        except Exception:
            logger.exception("failed to delete the account")
            await rollback_quietly(self.unit_of_work)
            raise

    def _confirmed(self, account, password: object, confirm_email: object) -> bool:
        if has_password(account):
            # Only the password path. `confirm_email` is not even looked at: an
            # account with a password must not be deletable by retyping an address
            # that is on screen.
            return password_confirms(account, password, self.password_hasher)
        # No password on the account, so no password could ever confirm it --
        # including `""`, which is what is actually stored.
        return email_confirms(account, confirm_email)
