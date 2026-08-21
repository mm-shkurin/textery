"""`OAuthAttributionParking` over Postgres. Never raises, on its own session.

Its own session for the usual reason: a failed analytics write must not poison
the transaction that is minting a CSRF state or creating an account.

`take` DELETES as it reads, in one statement. The handshake is single-use, so the
row's only purpose is spent the moment the callback reads it -- and a delete that
returns what it removed cannot be raced into reading the same campaign twice.
"""

from collections.abc import Callable

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from access.analytics.fail_open import in_own_session
from analytics.attribution import FIELD_NAMES
from model.analytics.oauth_attribution_model import OAuthAttributionModel


class SqlAlchemyOAuthAttributionParking:
    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._session_factory = session_factory

    async def park(self, state_value: str, campaign_parameters: dict[str, str | None]) -> None:
        parked = {name: campaign_parameters.get(name) for name in FIELD_NAMES}
        if not any(parked.values()):
            # Nothing to carry. Writing a row of five NULLs would cost the handshake
            # an INSERT to tell the callback what it already assumes.
            return

        async def write(session: AsyncSession) -> None:
            await session.execute(
                pg_insert(OAuthAttributionModel)
                .values(state_value=state_value, **parked)
                .on_conflict_do_nothing(index_elements=["state_value"])
            )
            await session.commit()

        await in_own_session(self._session_factory, "oauth attribution was not parked", write, None)

    async def take(self, state_value: str) -> dict[str, str | None]:
        async def take_row(session: AsyncSession) -> dict[str, str | None]:
            result = await session.execute(
                delete(OAuthAttributionModel)
                .where(OAuthAttributionModel.state_value == state_value)
                .returning(*(getattr(OAuthAttributionModel, name) for name in FIELD_NAMES))
            )
            row = result.first()
            await session.commit()
            return dict(zip(FIELD_NAMES, row, strict=True)) if row is not None else {}

        return await in_own_session(
            self._session_factory, "oauth attribution was not read back", take_row, {}
        )
