import uuid

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from model.base import Base


class GenerationVisitorModel(Base):
    """Which browser asked for a generation, remembered until it completes.

    A TABLE OF ITS OWN rather than a column on `generations`, and that is the
    story's governing decision made structural. A generation's visitor is an
    analytics fact: nothing in the product reads it, no domain rule depends on
    it, and the `Generation` entity's fields are enumerated by hand in three
    places whose own docstring names "a field added to two of them" as the
    standing hazard. Adding an eleventh field there for a marketing join would
    put a product entity at risk for an analytics need.

    The row is written when the generation is requested and read when it
    completes -- possibly on a different instance, which is why it is in the
    database rather than in memory (§9.2), and why it survives a requeue (§9.10):
    nothing deletes it when the generation is retried.

    No foreign key to `generations`. The lifetimes are deliberately independent:
    a generation deleted with its owner's account must not fail on this row, and
    an orphan here is one unread row rather than a broken erasure (§11.4).
    """

    __tablename__ = "generation_visitors"

    generation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    visitor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
