"""registration attribution and technical context on accounts

Ten nullable columns, added in one revision: the five campaign parameters a
marketing link carries and the five things the server itself observed about the
caller that registered (`14_AnalyticsEventTracking.md` §4).

All ten are NULLABLE with no default and no backfill, deliberately. Every account
that exists before this revision registered before there was anything to record,
and inventing a value for them -- `''`, `UNKNOWN`, the deployment's own country --
would make the migration itself the largest fabricated cohort in the data. NULL
reads as "not recorded", which is the true statement (`01_API_Tests.md` §7.3).

This revision is also the MERGE POINT for the two heads this branch had:
`c5d6e7f8a9b0` (the analytics_events table) and `c4d5e6f7a8b9` (generations text
style) were both leaves, so `alembic upgrade head` had no single target. They are
independent -- one adds a table, the other a column on `generations` -- so
merging them is a bookkeeping fix, not a schema decision.

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0, c4d5e6f7a8b9
Create Date: 2026-08-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d6e7f8a9b0c1"
down_revision: Union[str, Sequence[str], None] = ("c5d6e7f8a9b0", "c4d5e6f7a8b9")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Written out as literals rather than imported from the domain, because a
# migration is a historical artifact: it must keep creating the columns it
# created on the day it ran, even after the domain's own list moves on.
_COLUMNS = (
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term",
    "registration_ip",
    "registration_country",
    "device_type",
    "operating_system",
    "device_language",
)


def upgrade() -> None:
    for column in _COLUMNS:
        op.add_column("accounts", sa.Column(column, sa.Text(), nullable=True))


def downgrade() -> None:
    for column in reversed(_COLUMNS):
        op.drop_column("accounts", column)
