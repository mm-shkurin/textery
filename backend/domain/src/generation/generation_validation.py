"""The field rules `Generation.create` applies, as functions rather than methods.

Split out for file size, on the same grounds `generation_rules` was: `generation`
had grown past the 200-line limit and these three were the part with no reference
to `self` -- every one was already a `@staticmethod`, which is to say already not
about a particular generation.

They are imported by `generation`, and only by it. Nothing here re-exports: the
constants stayed in `generation_rules` and are imported from there by both
modules, so there is still one definition of each message.
"""

import unicodedata

from document.document_type import DocumentType
from generation.generation_rules import (
    INVALID_DOCUMENT_TYPE_MESSAGE,
    MAX_VOLUME_PAGES,
    MIN_VOLUME_PAGES,
    MISSING_TOPIC_MESSAGE,
)
from shared.exceptions import ValidationException


def validate_document_type(document_type: str) -> str:
    """Reject anything outside the four supported types.

    Load-bearing, not cosmetic: the composed prompt interpolates this value
    straight into the text sent to the model ("{document_type} на тему: {topic}"),
    so an unvalidated string here reaches it. The generations table carries no
    CHECK on the column either -- unlike documents -- which makes this the only
    guard.

    DocumentType is reused rather than reimplemented so the allowlist stays one
    tuple, shared with Document.create and the documents CHECK constraint.
    """
    try:
        return DocumentType(document_type).value
    except ValueError as error:
        # error_code="INVALID_DOCUMENT_TYPE", matching CreateDocument, rather than
        # the bare VALIDATION_ERROR this factory's other rules raise. It is the
        # same field under the same allowlist, so a client that learned to handle
        # the code from /documents handles it here unchanged -- and the shared
        # handler already maps it to 422.
        raise ValidationException(
            error_code="INVALID_DOCUMENT_TYPE",
            message=INVALID_DOCUMENT_TYPE_MESSAGE,
        ) from error


def is_out_of_range_volume(volume_pages: int | None) -> bool:
    if volume_pages is None:
        return True
    return not (MIN_VOLUME_PAGES <= volume_pages <= MAX_VOLUME_PAGES)


def required_topic(topic: str | None) -> str:
    """The topic, proven present, or `MISSING_TOPIC_MESSAGE`.

    Returns the value rather than answering a yes/no question, so the caller holds
    a `str` afterwards instead of a `str | None` it has to remember is already
    checked.
    """
    if topic is None:
        raise ValidationException(MISSING_TOPIC_MESSAGE)
    # str.strip() only removes Unicode whitespace (category Zs/Zl/Zp), not format
    # characters like U+200B ZERO WIDTH SPACE (category Cf). Strip both ordinary
    # whitespace and format characters before checking emptiness.
    visible_chars = [
        char for char in topic if not char.isspace() and unicodedata.category(char) != "Cf"
    ]
    if not visible_chars:
        raise ValidationException(MISSING_TOPIC_MESSAGE)
    return topic
