"""The one rule both child-scope guards build their refusal record by.

`resolve_owned_edit` and `resolve_owned_revision` refuse at the same two steps
for the same two reasons, and the record they emit follows one rule: always
carry the caller's own id, never carry the peer id the caller failed to prove a
claim to. Two hand-written `extra` dicts drift on exactly that distinction, and
they drift silently -- each guard's own tests pin only its own literals, so both
stay green while the shape diverges. Hence one function, and a cross-guard test
(`refusal_record_shape_statements`) that reads both guards' emitted records.

The logger and the message are parameters rather than module constants: the two
guards deliberately emit under their own logger names and their own one-line
messages, so the `logging.info` call is the only thing shared -- which is
precisely the part that carries the rule.
"""

import logging
from uuid import UUID

# Step 1's cause, identical for both guards: the document in the path could not
# be resolved as the caller's own, whether it is absent or somebody else's.
DOCUMENT_SCOPE_REFUSAL_CAUSE = "document-scope-refused"


def log_refusal(
    logger: logging.Logger,
    message: str,
    cause: str,
    owner_id: UUID,
    document_id: UUID | None = None,
) -> None:
    """Emit the refusal record, carrying only ids the caller has proven a claim to.

    The optional `document_id` is the whole non-disclosure rule in one signature.
    Step 1 refused precisely because the caller has no proven claim to the id in
    the path, so that id must not reach our logs; step 2 refused with the document
    already resolved as the caller's own, and recording it is what tells a probe
    apart from a typo'd document id. `caller_id` is never optional -- "id-free"
    means the message and the peer ids, never the caller's own id, which is what
    makes a refusal attributable at all.
    """
    fields = {"refusal_cause": cause, "caller_id": str(owner_id)}
    if document_id is not None:
        fields["document_id"] = str(document_id)
    # `stacklevel=2` attributes the record to the guard that refused, not to this
    # line. Without it every refusal in both guards reports `refusal_log.py` as
    # its `filename`/`lineno`/`funcName`, so an operator grepping by source
    # location -- or any formatter carrying `%(filename)s:%(lineno)d` -- sees one
    # location for all four refusal sites. No test reads those attributes (the
    # cross-guard shape check subtracts every standard `LogRecord` field before
    # comparing), which is exactly why the regression was silent when the two
    # per-guard `_log_refusal` bodies were folded into this one.
    logger.info(message, extra=fields, stacklevel=2)
