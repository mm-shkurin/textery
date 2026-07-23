from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from auth.oauth_state import OAuthState
from model.auth.oauth_state_model import OAuthStateModel


class SqlAlchemyOAuthStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, state: OAuthState) -> None:
        self._session.add(OAuthStateModel.from_domain(state))
        await self._session.flush()

    async def consume(self, value: str) -> OAuthState | None:
        """Delete-and-return in one statement, so the state is single-use.

        `DELETE ... RETURNING` removes the row and hands back its columns atomically:
        a replayed callback runs the same delete, matches nothing, and gets None. The
        caller commits — the row lock the delete takes is held until then, so two legs
        racing one state cannot both come away with it. No commit here; the caller owns
        the transaction boundary.
        """
        result = await self._session.execute(
            delete(OAuthStateModel)
            .where(OAuthStateModel.value == value)
            .returning(
                OAuthStateModel.value,
                OAuthStateModel.provider,
                OAuthStateModel.created_at,
                OAuthStateModel.expires_at,
            )
        )
        row = result.one_or_none()
        if row is None:
            return None
        return OAuthState(
            value=row.value,
            provider=row.provider,
            created_at=row.created_at,
            expires_at=row.expires_at,
        )
