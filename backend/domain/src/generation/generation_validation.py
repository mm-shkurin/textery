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
    OUT_OF_RANGE_VOLUME_MESSAGE,
)
from shared import error_codes
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
        # error_code=error_codes.INVALID_DOCUMENT_TYPE, matching CreateDocument, rather than
        # the bare VALIDATION_ERROR this factory's other rules raise. It is the
        # same field under the same allowlist, so a client that learned to handle
        # the code from /documents handles it here unchanged -- and the shared
        # handler already maps it to 422.
        raise ValidationException(
            error_code=error_codes.INVALID_DOCUMENT_TYPE,
            message=INVALID_DOCUMENT_TYPE_MESSAGE,
        ) from error


def is_out_of_range_volume(volume_pages: int | None) -> bool:
    """True for anything this field may not be: absent, out of bounds, or a bool.

    `bool` is excluded EXPLICITLY, and it is not a theoretical case. `bool`
    subclasses `int`, so Pydantic coerces a JSON `true` to `1` on the way in and
    `1 <= 1 <= 10` then passes -- measured against the running stack 2026-08-20:
    `{"volume_pages": true}` produced a one-page generation the caller never asked
    for, on both the create and the retry path, and billed it.

    The same trap is already guarded in two other places for the same reason --
    `PageRequest._validated_limit` (a JSON `true` limit) and
    `prompt_template._is_renderable_volume` (which would otherwise render
    "True стр."). This is the third, and it is the one that decides whether the
    row is written at all, so closing it here is what stops the value reaching
    either of the others.
    """
    if isinstance(volume_pages, bool):
        return True
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


def validated_retry_volume(volume_pages: int) -> int:
    """A retry's requested length, proven inside the range the form allows.

    `is_out_of_range_volume` answers the question; this raises the refusal, so the
    caller holds an `int` afterwards instead of a value it has to remember is
    already checked -- the same shape `required_topic` has, for the same reason.

    Reuses the predicate and the message `Generation.create` applies, so «изменить
    объём» cannot accept a length the original form would have refused. Without
    it a client could ask for 500 pages, the row would store it, and `build_prompt`
    would then reject the value as unrenderable -- turning a client mistake into a
    generation that fails after the work was queued.

    It is NOT applied to the volume a retry COPIES from its source. That value is
    history: a row created under an older, wider rule must stay retryable, which
    is the whole reason `retry_of` re-validates overrides and nothing else.
    """
    if is_out_of_range_volume(volume_pages):
        raise ValidationException(OUT_OF_RANGE_VOLUME_MESSAGE)
    return volume_pages
