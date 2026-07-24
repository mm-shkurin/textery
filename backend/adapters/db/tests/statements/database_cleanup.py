"""The one place that knows how to empty the test database.

It lived in four places before -- `conftest.py` plus a private copy in each of
the three CAS/concurrency tests that build their own engine. The list drifted
exactly the way four copies of a list drift: story 16's migrations added the
`oauth_*` tables, `oauth_identities` references `accounts`, and every copy kept
truncating the old four. Postgres then refused the statement outright, cleanup
stopped happening, and tests began failing on leftover rows from earlier tests
rather than on anything they asserted.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

# One statement, because Postgres refuses to truncate a table another table
# references unless every referencing table goes in the same command.
#
# CASCADE is belt-and-braces on top of the explicit list: a future table that
# references one of these is truncated with it rather than breaking the suite the
# same way again. The list still enumerates every table, because CASCADE only
# reaches tables connected by a foreign key -- `oauth_states` and
# `oauth_rate_limits` have none and would otherwise never be cleaned.
TRUNCATE_ALL = (
    "TRUNCATE TABLE generations, documents, verification_codes, oauth_identities, "
    "oauth_handoff_codes, oauth_states, oauth_rate_limits, accounts CASCADE"
)


async def truncate_all(engine: AsyncEngine) -> None:
    """Empty every table, on a connection of its own."""
    async with engine.connect() as cleanup_connection:
        await cleanup_connection.execute(text(TRUNCATE_ALL))
        await cleanup_connection.commit()
