"""constrain generations.document_type to the supported set

The documents table has constrained this column since it was created; the
generations table never did. Generation._validate_document_type is the only
guard, so any code path that writes a row without going through the factory --
a migration, a fixture, a future bulk import -- can put an arbitrary string in a
column whose value GigaChatProvider interpolates straight into an LLM prompt.

The allowlist is not restated here: it is read from the domain's
SUPPORTED_DOCUMENT_TYPES, the same tuple the documents constraint and both
factories use, so the four values stay single-sourced.

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

from document.document_type import SUPPORTED_DOCUMENT_TYPES

revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, None] = "c9d0e1f2a3b4"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None

_CONSTRAINT_NAME = "ck_generations_document_type"
_ALLOWED_DOCUMENT_TYPES_SQL = ", ".join(repr(value) for value in SUPPORTED_DOCUMENT_TYPES)


def upgrade() -> None:
    # Existing rows are reconciled first: the column was unconstrained, so this
    # environment may hold values the constraint would reject and ADD CONSTRAINT
    # would fail on. They cannot be repaired -- the original intent is not
    # recoverable from a free-text string -- so they are failed with the same
    # generic message the provider path uses, which is what those generations
    # would have got had the guard existed.
    op.execute(
        sa.text(
            f"""
            UPDATE generations
               SET status = 'failed',
                   error_message = :message
             WHERE document_type NOT IN ({_ALLOWED_DOCUMENT_TYPES_SQL})
               AND status <> 'failed'
            """
        ).bindparams(message="Не удалось сгенерировать документ. Попробуйте позже.")
    )
    op.execute(
        sa.text(
            f"""
            UPDATE generations
               SET document_type = :fallback
             WHERE document_type NOT IN ({_ALLOWED_DOCUMENT_TYPES_SQL})
            """
        ).bindparams(fallback=SUPPORTED_DOCUMENT_TYPES[0])
    )
    op.create_check_constraint(
        _CONSTRAINT_NAME,
        "generations",
        f"document_type IN ({_ALLOWED_DOCUMENT_TYPES_SQL})",
    )


def downgrade() -> None:
    op.drop_constraint(_CONSTRAINT_NAME, "generations", type_="check")
