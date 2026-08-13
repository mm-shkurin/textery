"""DSL for account deletion against a real Postgres.

A test on fakes would be worse than useless here, twice over: fakes know nothing
about foreign keys, so they go green on a delete order Postgres refuses with
IntegrityError, and nothing about `ON DELETE CASCADE`, so they cannot show that
`generations` really do go with the account. Both halves live in the database.

Every read-back opens a session of its own -- with `expire_on_commit=False` a
re-read on the writing session is answered from the identity map.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from access.auth.account_eraser import SqlAlchemyAccountEraser
from access.auth.account_storage import SqlAlchemyAccountRepository
from auth.delete_account import DeleteAccount
from auth.deletion_confirmation import DELETION_CONFIRMATION_INVALID_CODE
from session import SqlAlchemyUnitOfWork
from shared.exceptions import ValidationException
from statements.account_deletion_fixtures import (
    PASSWORD_HASH,
    all_one,
    all_zero,
    count_every_table,
    seed_full_account,
)


class _StubHasher:
    """Verifies, or refuses, on command.

    A stub rather than the real hasher, and it does NOT weaken these tests: what
    this file asks is what a CONFIRMED and a REFUSED deletion do to the rows, so
    "the confirmation passed" / "it did not" is the whole of what a hasher
    contributes. WHICH confirmations actually pass -- and that an empty password
    never does -- is proven end to end against the real hasher over HTTP, where
    that claim belongs.
    """

    def __init__(self, accepts: bool) -> None:
        self._accepts = accepts

    def hash(self, plain_password: str) -> str:
        return PASSWORD_HASH

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        return self._accepts


class AccountDeletionStatements:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._owner: UUID | None = None
        self._bystander: UUID | None = None
        self._refusal_code: str | None = None
        self._counts: dict[UUID, dict[str, int]] = {}

    async def given_two_full_accounts(self) -> None:
        """Two accounts, each with a row in every table that references an account.

        The second one is not decoration: a `DELETE` whose owner predicate is
        missing or wrong empties the table for EVERYONE, and against a
        single-account fixture that mistake is invisible -- every assertion about
        the deleted account still passes.
        """
        self._owner = await seed_full_account(self._session_factory)
        self._bystander = await seed_full_account(self._session_factory)

    async def delete_the_owner_with_a_valid_confirmation(self) -> None:
        await self._run_deletion(accepts=True)

    async def try_to_delete_the_owner_with_a_wrong_password(self) -> None:
        await self._run_deletion(accepts=False)

    async def count_every_table_for_both_accounts(self) -> None:
        for account_id in (self._required(self._owner), self._required(self._bystander)):
            self._counts[account_id] = await count_every_table(self._session_factory, account_id)

    def assert_the_owner_is_gone_from_every_table(self) -> None:
        counts = self._counts[self._required(self._owner)]
        assert counts == all_zero(), (
            f"expected no row of the deleted owner anywhere, got {counts!r}. A non-zero "
            "generations count means the ON DELETE CASCADE did not fire; a non-zero "
            "documents count means the explicit delete is missing -- that table carries no "
            "foreign key, so nothing else would ever remove the user's text."
        )

    def assert_the_bystander_is_untouched(self) -> None:
        counts = self._counts[self._required(self._bystander)]
        assert counts == all_one(), (
            f"expected the other account to keep every row, got {counts!r}. A zero here "
            "means a DELETE ran without its owner predicate."
        )

    def assert_the_refusal_left_everything_in_place(self) -> None:
        assert self._refusal_code == DELETION_CONFIRMATION_INVALID_CODE, (
            f"expected {DELETION_CONFIRMATION_INVALID_CODE}, got {self._refusal_code!r}"
        )
        for described_as, account_id in (
            ("the refused account", self._required(self._owner)),
            ("the other account", self._required(self._bystander)),
        ):
            counts = self._counts[account_id]
            assert counts == all_one(), (
                f"expected {described_as} to keep every row after a refused deletion, got "
                f"{counts!r}. A refusal that deletes anything first is not a refusal."
            )

    async def _run_deletion(self, accepts: bool) -> None:
        async with self._session_factory() as session:
            usecase = DeleteAccount(
                account_repository=SqlAlchemyAccountRepository(session),
                account_eraser=SqlAlchemyAccountEraser(session),
                password_hasher=_StubHasher(accepts),
                # The real UnitOfWork on the eraser's own session: all five
                # statements are one transaction, and without the commit they
                # would be rolled back on close while the caller was told the
                # account was gone.
                unit_of_work=SqlAlchemyUnitOfWork(session),
            )
            try:
                await usecase.execute(
                    account_id=self._required(self._owner), password="whatever-was-typed"
                )
                self._refusal_code = None
            except ValidationException as error:
                self._refusal_code = error.error_code

    @staticmethod
    def _required(account_id: UUID | None) -> UUID:
        assert account_id is not None, "no account arranged: call given_two_full_accounts first"
        return account_id
