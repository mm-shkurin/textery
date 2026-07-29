"""Whole-entity comparison and the save boundary's content payloads.

Split out of `save_document_statements.py` only to keep that file under the
200-line cap; it is the same DSL.
"""

from document.document import Document

# The content cap the save boundary enforces, with the payloads that sit either
# side of it. Owned here so the test classes never build an expected value from
# the same expression they submitted.
MAX_CONTENT = 200_000
CONTENT_AT_THE_MAXIMUM = "a" * MAX_CONTENT
CONTENT_PAST_THE_MAXIMUM = "a" * (MAX_CONTENT + 1)


def state_of(document: Document) -> tuple:
    """EVERY field of the entity, in one comparable value.

    Named per-field rather than compared as objects: `Document` has no
    `__eq__`, and the fake mutates and returns the SAME instance it stores, so
    `stored == saved` is an identity check that can never fail. A field tuple is
    the only comparison here that actually reads the values -- and it is what
    makes a partial "content and version match" assertion impossible to write by
    accident, so a save that quietly rewrote `title` or `updated_at` goes red.
    """
    return (
        document.id,
        document.owner_id,
        document.document_type,
        document.status,
        document.content,
        document.version,
        document.idempotency_key,
        document.created_at,
        document.updated_at,
        document.title,
    )
