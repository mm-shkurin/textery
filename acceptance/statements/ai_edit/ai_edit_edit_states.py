"""The AI-edit lifecycle states, in one place.

Vocabulary only — no client, no HTTP, no assertions. `queued` was spelled once in
scenario 1.2's seed assertion and again inside the reachable-states tuple its outcome
assertion pins; two spellings of one concept drift apart silently, the same reason
`ai_edit_http_status` exists.

Names are the five states enumerated by documents_ai_edits_get.yaml.
"""

QUEUED_STATUS = "queued"
STREAMING_STATUS = "streaming"
DONE_STATUS = "done"
ERROR_STATUS = "error"
CANCELLED_STATUS = "cancelled"

# A queued edit legitimately advances queued -> streaming -> done (or -> error) under
# the worker with nobody cancelling it, so those four are the states reachable WITHOUT
# a cancel. `cancelled` is the single state only a cancel can produce — asserting
# positive membership in this set, rather than `!= CANCELLED_STATUS`, also rejects a
# missing, misspelled or junk status that a negative check would wave through.
STATES_REACHABLE_WITHOUT_A_CANCEL = (
    QUEUED_STATUS,
    STREAMING_STATUS,
    DONE_STATUS,
    ERROR_STATUS,
)

# The same five states partitioned by whether the worker can still move them. A poll
# that waits for an edit to settle needs both halves: it stops on a terminal state and
# rejects anything in neither half as an unknown state, rather than looping on junk.
TERMINAL_STATES = (DONE_STATUS, ERROR_STATUS, CANCELLED_STATUS)
NON_TERMINAL_STATES = (QUEUED_STATUS, STREAMING_STATUS)
