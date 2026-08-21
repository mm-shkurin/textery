"""Bounds, refusal messages and status values for `Generation`, and the rules they serve.

Split out of `generation.py` to keep that file under the 200-line cap. They are
re-exported from there, so `from generation.generation import PENDING_STATUS`
keeps working -- moving a constant must not become a rename for every caller.

The prose below moved here for the same reason, from the construction paths in
`generation.py` whose bodies it had grown longer than the 30-line function limit.
It is the rules themselves, so this is where they belong.

CONSTRUCTION: `__init__` (hydration)
------------------------------------
`owner_id` is required positionally, with no default: a default would let a
caller that forgot the owner construct an unowned generation and only fail later
at the NOT NULL column, far from the mistake.

`idempotency_key` and `source_generation_id` both default to None because every
generation created before retries existed has neither. NULL is "no key was ever
supplied", which is a different statement from "the empty key" -- and the one the
unique index needs, since Postgres treats NULLs as distinct.

`text_style` is unvalidated here, like every other field on this path: `__init__`
is the storage hydration route, and a row written under an older allowlist must
read back as it was rather than raise on a value the user cannot change.
`style_instruction` is what degrades an unrecognised value to no sentence at all
when the prompt is built.

CONSTRUCTION: `create`
----------------------
The topic is rebound to the non-optional return of `required_topic`, and that is
what lets the length check be honest: a predicate that answers True for None
leaves `topic` typed `str | None` afterwards, and `len(topic)` was only safe by
reading the two lines together. The validator returns the narrowed value instead.

CONSTRUCTION: `retry_of`
------------------------
A fresh run of a source generation, from the parameters stored on that row.

Every field EXCEPT the two named overrides is copied from the source row rather
than taken from the request, which is what keeps the retry endpoint bodiless in
its plain form: there is no `owner_id`, `status`, `id` or timestamp for a client
to over-bind, because none of them is read from a client at all.

The new row starts `pending` with a server-assigned id and creation instant --
never the source's status, and never `completed` carried across, which would
produce a finished generation that was never run.

**Copied fields are deliberately NOT re-validated.** The source row is already
stored, and refusing here would strand a user whose generation was created under
an older, wider rule with a button that can never succeed. A document type that
is no longer offered is caught downstream by the provider.

**The overrides ARE validated**, and the asymmetry is the point: a copied value
is history, which the user cannot change and must not be punished for, while an
override is a fresh choice arriving from a client right now. The same value gets
opposite treatment depending on where it came from, which is why the two are
resolved by the `_overridden_*` helpers rather than by one rule applied to the
whole row.

`None` on an override means "not overridden", never "clear it". Neither register
nor length has a meaningful empty state a user would ask for, so no caller needs
to say the other thing and no caller can say it by accident.

The overrides are keyword-only, and not for style: `text_style` is a `str` and
`volume_pages` an `int`, so a transposition would be caught today -- but a third
override of either type would not be, and the barrier costs nothing now while
adding it later costs every call site.

«Перегенерировать в другом стиле» and «изменить объём» are the two things a user
genuinely re-chooses at the moment of a retry. An absent override keeps the
source's own value, so the plain «Повторить» button stays bodiless.
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
