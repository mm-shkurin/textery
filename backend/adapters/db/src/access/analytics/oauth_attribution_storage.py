"""`OAuthAttributionParking` over Postgres. Never raises, on its own session.

Its own session for the usual reason: a failed analytics write must not poison
the transaction that is minting a CSRF state or creating an account.

`take` DELETES as it reads, in one statement. The handshake is single-use, so the
row's only purpose is spent the moment the callback reads it -- and a delete that
returns what it removed cannot be raced into reading the same campaign twice.
"""

import logging
from collections.abc import Callable

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from analytics.attribution import FIELD_NAMES
from model.analytics.oauth_attribution_model import OAuthAttributionModel

logger = logging.getLogger(__name__)


class SqlAlchemyOAuthAttributionParking:
    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._session_factory = session_factory

    async def park(self, state_value: str, campaign_parameters: dict[str, str | None]) -> None:
        parked = {name: campaign_parameters.get(name) for name in FIELD_NAMES}
        if not any(parked.values()):
            # Nothing to carry. Writing a row of five NULLs would cost the handshake
            # an INSERT to tell the callback what it already assumes.
            return
        session = self._session_factory()
        try:
            await session.execute(
                pg_insert(OAuthAttributionModel)
                .values(state_value=state_value, **parked)
                .on_conflict_do_nothing(index_elements=["state_value"])
            )
            await session.commit()
        except Exception as error:
            logger.warning("oauth attribution was not parked: %s", type(error).__name__)
        finally:
            await session.close()

    async def take(self, state_value: str) -> dict[str, str | None]:
        session = self._session_factory()
        try:
            result = await session.execute(
                delete(OAuthAttributionModel)
                .where(OAuthAttributionModel.state_value == state_value)
                .returning(*(getattr(OAuthAttributionModel, name) for name in FIELD_NAMES))
            )
            row = result.first()
            await session.commit()
            return dict(zip(FIELD_NAMES, row, strict=True)) if row is not None else {}
        except Exception as error:
            logger.warning("oauth attribution was not read back: %s", type(error).__name__)
            return {}
        finally:
            await session.close()
