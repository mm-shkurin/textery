from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.oauth_identity import OAuthIdentity
from model.auth.oauth_identity_model import OAuthIdentityModel


class SqlAlchemyOAuthIdentityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find(self, provider: str, subject: str) -> OAuthIdentity | None:
        result = await self._session.execute(
            select(OAuthIdentityModel).where(
                OAuthIdentityModel.provider == provider,
                OAuthIdentityModel.subject == subject,
            )
        )
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def save(self, identity: OAuthIdentity) -> None:
        self._session.add(OAuthIdentityModel.from_domain(identity))
        await self._session.flush()
