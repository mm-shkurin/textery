import logging
from uuid import UUID

from auth.account import Account
from auth.account_name import AccountName
from auth.account_repository import AccountRepository
from auth.profile_errors import unauthorized
from shared.rollback import rollback_quietly
from shared.unit_of_work import NullUnitOfWork, UnitOfWork

logger = logging.getLogger(__name__)


class RenameAccount:
    """Set or clear the caller's display name, and answer with the whole profile.

    The whole profile, not an echo of the request: the stored value is the
    NORMALIZED one, so an NFD request comes back canonically equivalent but not
    byte-equal and a trailing space comes back trimmed. A client that recomputed
    its dirty flag against what it sent would show "unsaved" forever after a
    successful save of a name with a trailing space.

    Last-write-wins, deliberately: no version, no If-Match, no 409. Because
    clearing is first-class, a stale tab can UNDO a rename rather than merely
    overwrite it. Accepted for a display name -- the cost of a lost update is one
    retype -- and written down here so it is not read as an oversight.
    """

    def __init__(
        self,
        account_repository: AccountRepository,
        unit_of_work: UnitOfWork | None = None,
    ) -> None:
        self._account_repository = account_repository
        # A real UnitOfWork bound to the SAME session as the repository is not
        # optional in production: NullUnitOfWork's commit() is a silent no-op, so a
        # mis-wired usecase answers 200, returns the new name, and persists
        # nothing, with no error anywhere. test_login_wiring.py exists because that
        # already happened once.
        self._unit_of_work = unit_of_work or NullUnitOfWork()

    async def execute(self, account_id: UUID, name: object) -> Account:
        # Validated BEFORE the account is read, so a malformed name costs zero
        # queries and cannot be distinguished by timing from a well-formed one
        # against a missing account.
        normalized = AccountName(name).value
        account = await self._account_repository.find_by_id(account_id)
        if account is None:
            raise unauthorized()
        try:
            # update_name, not save(): save()'s update branch also writes email,
            # password_hash and is_verified from the snapshot read a moment ago, so
            # a rename racing a verification would put the pre-verify value back.
            # This UPDATE sets one column.
            #
            # Called unconditionally -- there is no `if normalized:` here. That
            # guard is exactly how "clear my name" becomes a 200 that changes
            # nothing, because the cleared value IS None.
            await self._account_repository.update_name(account_id, normalized)
            await self._unit_of_work.commit()
        except Exception:
            logger.exception("failed to persist the renamed account")
            await rollback_quietly(self._unit_of_work)
            raise
        # The entity was read before the UPDATE, so it still carries the old name;
        # applying the change here is what makes the returned profile the state the
        # client should now hold. Re-reading instead would cost a second SELECT to
        # learn a value this process just decided.
        account.rename(normalized)
        return account
