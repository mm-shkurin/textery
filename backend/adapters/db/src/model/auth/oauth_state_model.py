from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from auth.oauth_state import OAuthState
from model.base import Base


class OAuthStateModel(Base):
    __tablename__ = "oauth_states"

    # The state value itself is the primary key: it is server-minted, unique, and the
    # only thing ever looked up. Consumption is a delete of this row, which is what
    # makes the state single-use across the two request legs.
    value: Mapped[str] = mapped_column(String, primary_key=True)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @classmethod
    def from_domain(cls, state: OAuthState) -> "OAuthStateModel":
        return cls(
            value=state.value,
            provider=state.provider,
            created_at=state.created_at,
            expires_at=state.expires_at,
        )

    def to_domain(self) -> OAuthState:
        return OAuthState(
            value=self.value,
            provider=self.provider,
            created_at=self.created_at,
            expires_at=self.expires_at,
        )
