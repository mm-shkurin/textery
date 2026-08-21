"""The SET clause of a document save, as a function.

Moved out of `SqlAlchemyDocumentStorage` when that file passed the 200-line cap.
It reads no session and no row — it is a pure mapping from a save's intent to the
columns that intent touches, which is why it needs no class around it.

`title` is included ONLY when the caller carries an intent. A content-only
autosave omits it, and SETting title = NULL unconditionally would silently wipe
the user's title.

Whether an intent names a title is `TitleUpdate`'s own question, asked as
`carries_a_value()` -- the adapter does not re-derive `preserve()` by
null-testing `value`.

A raw `str` is no longer accepted, and the blank path is closed at the source:
`TitleUpdate.__post_init__` folds a blank value down to preserve on EVERY
construction path, so no intent reaching here can carry `""` and `SET title = ''`
is unreachable. Blankness is no longer decided one layer up in `SaveDocument`; it
is an invariant of the type, which is why an adapter built by some other caller
cannot reopen it.

There is no `| None` arm: the absent case reaches here as `preserve()`, so the
intent is always named.

⚠️ STILL TWO BRANCHES, and the third state is UNMAPPED: `clear()` is also
`carries_a_value() == False`, so it currently falls into the omit branch and
no-ops. The `SET title = NULL` arm (ask `title.erases()` first) is owned by the
routed `adapters-discovery` (b) step.
"""

from datetime import datetime
from typing import Any

from document.title_update import TitleUpdate
from model.document.document_model import DocumentModel


def update_values(content: str, updated_at: datetime, title: TitleUpdate) -> dict[str, Any]:
    """The SET clause. See the module docstring for the title rules."""
    values: dict[str, Any] = {
        "content": content,
        "version": DocumentModel.version + 1,
        "updated_at": updated_at,
    }
    if title.carries_a_value():
        values["title"] = title.value
    return values
