from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from model.base import Base


class OAuthAttributionModel(Base):
    """The campaign parked against one OAuth handshake.

    Keyed on the state value, which is server-minted and single-use -- the row's
    lifetime is the handshake's, and the callback deletes it as it reads it.

    A TABLE OF ITS OWN rather than five columns on `oauth_states`: the state is a
    CSRF mechanism whose entity is mapped by hand in `from_domain`/`to_domain`,
    and marketing metadata has no business widening it. No foreign key, for the
    same reason as `generation_visitors`: an expired state pruned out from under
    an orphan row here costs one unread row, while a constraint would make an
    analytics table able to fail a security mechanism's cleanup.
    """

    __tablename__ = "oauth_state_attribution"

    state_value: Mapped[str] = mapped_column(String, primary_key=True)
    utm_source: Mapped[str | None] = mapped_column(String, nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String, nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String, nullable=True)
    utm_content: Mapped[str | None] = mapped_column(String, nullable=True)
    utm_term: Mapped[str | None] = mapped_column(String, nullable=True)
