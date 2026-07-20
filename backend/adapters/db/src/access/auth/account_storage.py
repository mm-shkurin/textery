from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from auth.account import Account
from model.auth.account_model import AccountModel
from shared.exceptions import ConflictException


class SqlAlchemyAccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_email(self, email: str) -> Account | None:
        # Exact match: callers pass Email(...).value, which is already
        # lowercased/NFC-normalized, and the uq_accounts_email constraint is on
        # that same canonical value. A case-insensitive query here would not
        # match how rows are stored.
        result = await self._session.execute(
            select(AccountModel).where(AccountModel.email == email)
        )
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def find_by_id(self, account_id: UUID) -> Account | None:
        model = await self._session.get(AccountModel, account_id)
        return model.to_domain() if model else None

    async def transition_to_verified(self, account_id: UUID) -> bool:
        """Atomically flip is_verified false->true for exactly one caller.

        Conditional single-row UPDATE (``WHERE is_verified = false``): the winning
        racer affects one row (``rowcount == 1`` -> True); every later racer sees the
        row already verified and affects zero rows (``rowcount == 0`` -> False). Zero
        rows is idempotent success, NOT an error (inverts generation_storage.py's
        zero-row->raise): the loser resolves to the already-verified state, no
        exception. No commit here -- the caller owns the transaction boundary.
        """
        result = await self._session.execute(
            update(AccountModel)
            .where(AccountModel.id == account_id, AccountModel.is_verified.is_(False))
            .values(is_verified=True)
        )
        return result.rowcount == 1

    async def save(self, account: Account) -> None:
        """Insert a new account, or update the one that already exists.

        Insert-only (a bare session.add) is what this used to do, which was
        invisible until /verify went live: registration always inserts, but
        verifying an account saves an Account that already has a row, so add()
        emitted a second INSERT with the same primary key and Postgres rejected it
        with accounts_pkey. The usecase's broad except turned that into a 500. The
        fakes append to a list, so no unit test could see it.
        """
        existing = await self._session.get(AccountModel, account.id)
        if existing is None:
            self._session.add(AccountModel.from_domain(account))
        else:
            existing.email = account.email
            existing.password_hash = account.password_hash
            existing.is_verified = account.is_verified
        try:
            await self._session.flush()
        except IntegrityError as error:
            raise ConflictException(f"account with email {account.email} already exists") from error
