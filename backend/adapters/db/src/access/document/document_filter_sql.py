"""The history filter, translated into SQL predicates.

Its own module rather than two private helpers on the storage class: with them
inline the storage file passed the 200-line cap, and the translation is a
self-contained mapping from one value object to a list of predicates — it reads
no session and touches no row.
"""

from typing import Any

from sqlalchemy import or_

from document.document_filter import DocumentFilter
from model.document.document_model import DocumentModel

# The character ILIKE is told to read as "the next one is literal". Bound as
# `escape=` on every pattern below, so it is one constant rather than a literal
# repeated at each call.
LIKE_ESCAPE = "\\"


def escaped_for_like(value: str) -> str:
    r"""Neutralise the wildcards so a search term is matched literally.

    A user searching for `100%` must not match every row in their history, and
    `_` must not stand in for any single character.

    The escape character itself is doubled FIRST: escaping `%` before `\` would
    then escape the backslash that was just introduced, and a term containing
    both would match nothing.
    """
    return (
        value.replace(LIKE_ESCAPE, LIKE_ESCAPE * 2)
        .replace("%", f"{LIKE_ESCAPE}%")
        .replace("_", f"{LIKE_ESCAPE}_")
    )


def filter_predicates(document_filter: DocumentFilter) -> list[Any]:
    """The narrowing, as SQL. An empty filter contributes nothing.

    The text match is `ILIKE` over title and content. There is no trigram index
    behind it, deliberately: the scan is over one account's own documents and is
    already bounded by the keyset page, so an index that must be created and
    maintained for dozens of rows is cost with no reader.

    `created_to` is inclusive (`<=`). A bare `YYYY-MM-DD` was already widened to
    that day's last instant when the filter was parsed, so an exclusive
    comparison here would make the two ends of the window mean different things.
    """
    predicates: list[Any] = []
    if document_filter.query is not None:
        pattern = f"%{escaped_for_like(document_filter.query)}%"
        predicates.append(
            or_(
                DocumentModel.title.ilike(pattern, escape=LIKE_ESCAPE),
                DocumentModel.content.ilike(pattern, escape=LIKE_ESCAPE),
            )
        )
    if document_filter.created_from is not None:
        predicates.append(DocumentModel.created_at >= document_filter.created_from)
    if document_filter.created_to is not None:
        predicates.append(DocumentModel.created_at <= document_filter.created_to)
    return predicates
