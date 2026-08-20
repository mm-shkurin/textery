"""Bounds, refusal messages and status values for `Generation`.

Split out of `generation.py` to keep that file under the 200-line cap. They are
re-exported from there, so `from generation.generation import PENDING_STATUS`
keeps working -- moving a constant must not become a rename for every caller.
"""

from document.document_type import SUPPORTED_DOCUMENT_TYPES
from shared import limits

MIN_VOLUME_PAGES = 1
MAX_VOLUME_PAGES = 10
MAX_TOPIC_LENGTH = limits.MAX_TOPIC_LENGTH
MAX_REQUIREMENTS_LENGTH = limits.MAX_REQUIREMENTS_LENGTH
MAX_EXTRA_WISHES_LENGTH = limits.MAX_EXTRA_WISHES_LENGTH
# Declared after the bounds and interpolated from them. These messages used to
# restate each number as a literal five lines from the constant it described, so
# changing a bound left the message quoting the old one -- the one place the
# discrepancy is guaranteed to be seen, by the user who just tripped the rule.
MISSING_TOPIC_MESSAGE = "topic is required"
OUT_OF_RANGE_VOLUME_MESSAGE = (
    f"volume_pages must be between {MIN_VOLUME_PAGES} and {MAX_VOLUME_PAGES}"
)
TOPIC_TOO_LONG_MESSAGE = f"topic must be at most {MAX_TOPIC_LENGTH} characters"
REQUIREMENTS_TOO_LONG_MESSAGE = f"requirements must be at most {MAX_REQUIREMENTS_LENGTH} characters"
EXTRA_WISHES_TOO_LONG_MESSAGE = f"extra_wishes must be at most {MAX_EXTRA_WISHES_LENGTH} characters"
INVALID_DOCUMENT_TYPE_MESSAGE = (
    f"document_type must be one of: {', '.join(SUPPORTED_DOCUMENT_TYPES)}"
)
PENDING_STATUS = "pending"
IN_PROGRESS_STATUS = "in_progress"
COMPLETED_STATUS = "completed"
FAILED_STATUS = "failed"
