"""The field vocabulary of `AiEditResponse`, derived once from documents_ai_edits_get.yaml.

Vocabulary only — no client, no HTTP, no assertions. Scenario 1.2's assertions and
scenario 1.3's revision seed were each hand-enumerating this schema, both citing the same
spec file: 1.2 as "known / required / done-only", 1.3 as "exactly what a done edit
carries". Two hand-written spellings of one schema drift apart while both stay green, so
the conditionality is stated once and the two enumerations are derived from it.

The spec's rule: three fields are always present; `version`, `revision_number` and
`changed` appear only on a `done` edit; `error_code` only on an `error` one; `last_seq`
is the event counter.
"""

REQUIRED_FIELDS = {"edit_id", "status", "created_at"}
DONE_ONLY_FIELDS = ("version", "revision_number", "changed")
ERROR_ONLY_FIELDS = ("error_code",)
EVENT_COUNTER_FIELD = "last_seq"

# Every field the endpoint may ever disclose. Anything outside this set is an
# undocumented disclosure — the tell that a handler leaked a raw row.
KNOWN_FIELDS = (
    REQUIRED_FIELDS
    | set(DONE_ONLY_FIELDS)
    | set(ERROR_ONLY_FIELDS)
    | {EVENT_COUNTER_FIELD}
)

# What a `done` edit carries EXACTLY: the always-present three, the three the spec makes
# conditional on `done`, and the counter — and no `error_code`, which only an `error`
# edit owns. An extra key is an undocumented disclosure, a missing one is the edit not
# having applied.
DONE_EDIT_FIELDS = KNOWN_FIELDS - set(ERROR_ONLY_FIELDS)
