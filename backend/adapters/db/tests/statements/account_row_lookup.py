from sqlalchemy import select
from sqlalchemy.engine import Row

from model.auth.account_model import AccountModel
from session import create_engine


async def fetch_account_row_on_new_connection(account_id) -> Row | None:
    """Read the accounts row through a brand-new connection/engine.

    Bypasses the test's own session so callers can verify durability
    (or absence) of a write independently of that session's cache.
    """
    engine = create_engine()
    async with engine.connect() as connection:
        result = await connection.execute(select(AccountModel).where(AccountModel.id == account_id))
        row = result.first()
    await engine.dispose()
    return row
