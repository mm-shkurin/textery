import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from auth.account import Account
from model.base import Base


class AccountModel(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    failed_attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", default=0
    )
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    # DEFERRED, and this is load-bearing rather than an optimisation. `GET /me`
    # runs on every authenticated page view -- it is the highest-rate query in the
    # product -- and an eagerly mapped `bytea` would add the whole image to every
    # one of those rows. Deferred, SQLAlchemy leaves the column out of the SELECT
    # entirely and emits a second query only if something reads the attribute.
    # Nothing does except the route that serves the image, which reads it through
    # an explicit column-list SELECT instead (see find_avatar). A SQL-capture test
    # pins that `avatar_bytes` never appears in the profile read's statement.
    avatar_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True, deferred=True)
    # Also deferred: it is small, but it is only ever needed together with the
    # bytes, and leaving it in the row would make "is it in the SELECT" a
    # judgement call for the next person instead of a rule.
    avatar_media_type: Mapped[str | None] = mapped_column(Text, nullable=True, deferred=True)
    # NOT deferred: this one IS part of the profile. It is the only avatar fact
    # `GET /me` reports, and it is a timestamp, not an image.
    avatar_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # The ten registration-context columns. Mapped so the model matches the
    # schema (Infra: `alembic upgrade head` against a model that omits a column
    # is a drift nothing catches), and ABSENT from `from_domain`/`to_domain` on
    # purpose -- the same arrangement `avatar_bytes` uses, and for the stronger
    # reason here. They are analytics metadata, not account behaviour: nothing in
    # the product reads them, they are written once by
    # `SqlAlchemyRegistrationContextWriter`'s targeted UPDATE, and putting them
    # on the entity would add them to three hand-kept column lists whose
    # docstring already names "a field added to two of them" as the standing
    # hazard. Analytics adapts to the application; the application does not grow
    # ten fields for it.
    utm_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(Text, nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(Text, nullable=True)
    utm_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    utm_term: Mapped[str | None] = mapped_column(Text, nullable=True)
    registration_ip: Mapped[str | None] = mapped_column(Text, nullable=True)
    registration_country: Mapped[str | None] = mapped_column(Text, nullable=True)
    device_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    operating_system: Mapped[str | None] = mapped_column(Text, nullable=True)
    device_language: Mapped[str | None] = mapped_column(Text, nullable=True)

    @classmethod
    def from_domain(cls, account: Account) -> "AccountModel":
        # Every column the entity carries is listed, and that completeness is the
        # point: this mapping used to omit failed_attempt_count, which was
        # invisible only because the column defaults to 0 and the sole caller is
        # registration, where 0 is right. `name` has no such alibi -- an INSERT
        # that skipped it would store NULL over a real value.
        #
        # There are three places that enumerate account columns by hand (here,
        # to_domain, and SqlAlchemyAccountRepository.save's update branch). A
        # field added to two of them produces a write that answers 200 and
        # persists nothing.
        #
        # `avatar_bytes` and `avatar_media_type` are ABSENT from all three on
        # purpose, so the hazard cannot apply to them: they never travel through
        # the entity at all. They are written by update_avatar/clear_avatar and
        # read by find_avatar, each naming its columns explicitly. Putting them on
        # `Account` would make this mapping read them, and reading a deferred
        # column is exactly the second query the deferral exists to prevent.
        return cls(
            id=account.id,
            email=account.email,
            password_hash=account.password_hash,
            is_verified=account.is_verified,
            created_at=account.created_at,
            failed_attempt_count=account.failed_attempt_count,
            name=account.name,
            avatar_updated_at=account.avatar_updated_at,
        )

    def to_domain(self) -> Account:
        # reconstitute, not the constructor: the constructor hardcodes
        # is_verified=False (correct for *creating* an account, wrong for reading
        # one back), which would make every stored account read as unverified --
        # no verified user could ever log in.
        return Account.reconstitute(
            id=self.id,
            email=self.email,
            password_hash=self.password_hash,
            created_at=self.created_at,
            is_verified=self.is_verified,
            failed_attempt_count=self.failed_attempt_count,
            name=self.name,
            # Only the timestamp. Reading self.avatar_bytes here would emit the
            # deferred load on every profile read and undo the whole arrangement.
            avatar_updated_at=self.avatar_updated_at,
        )
