"""SQL text for the CHECK constraints that mirror a domain allowlist.

Four columns constrain themselves to a list the domain owns -- `event_name`,
`document_type`, `documents.status` and `generations.status` -- and each model
built that list itself, with its own module-level `_..._SQL` constant and its own
f-string. One name for the idiom instead. The allowlist stays in the domain and
the database only constrains it; what matters is that the constraint is ITERATED
from the domain constants rather than written out as literals, so a name added
there without a migration turns `alembic upgrade head` red in CI instead of
drifting silently.

Migrations do NOT import this. They are historical artifacts and must keep
rendering the list they created against the domain catalogue as it was; a shared
helper would let a change here rewrite what an old revision means.
"""

from collections.abc import Iterable


def one_of(column: str, allowed: Iterable[str]) -> str:
    """Render `column IN ('A', 'B')` from the domain constants themselves.

    `repr` is what quotes each value, and it is exact for the values these
    allowlists hold: Python renders a string containing no apostrophe with single
    quotes, which is also SQL's string literal. A value carrying one would come
    out double-quoted -- a SQL *identifier* -- and fail the migration loudly on a
    column that does not exist, rather than storing anything wrong.
    """
    return f"{column} IN ({', '.join(repr(value) for value in allowed)})"
