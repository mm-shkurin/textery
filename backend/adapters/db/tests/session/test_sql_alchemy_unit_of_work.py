import pytest

from statements.sql_alchemy_unit_of_work_statements import SqlAlchemyUnitOfWorkStatements


class TestCommit:
    """Committing through the UnitOfWork port operates on the real shared
    AsyncSession, persisting a flushed-but-uncommitted account row durably —
    proving the adapter is a genuine wrapper around the session's transaction,
    not a no-op."""

    async def test_should_persist_flushed_account_after_commit(
        self, sql_alchemy_unit_of_work_statements: SqlAlchemyUnitOfWorkStatements
    ):
        account = sql_alchemy_unit_of_work_statements.build_account()
        await sql_alchemy_unit_of_work_statements.flush_account(account)
        await sql_alchemy_unit_of_work_statements.commit_unit_of_work()
        await sql_alchemy_unit_of_work_statements.assert_account_durable_on_new_connection()
