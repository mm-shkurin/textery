from statements.refusal_log_base import RefusalLogStatementsBase
from statements.revision_guard_base import RevisionGuardBase

# The logger the guard emits under, pinned as a literal so the record cannot be
# moved to a logger nobody collects and stay green.
GUARD_LOGGER_NAME = "document_edit.resolve_owned_revision"

# The one refusal line, identical for both causes and carrying no ids at all.
# Asserted with `==` rather than `in`: a substring check leaves the rest of the
# message unconstrained, so an id the guard was never supposed to record could ride
# along in text while every check for the *enumerated* ids passed. The whole-message
# equality is also what makes a separate "the probed number is not in the message"
# check unnecessary -- and it was worse than unnecessary: pinned to this literal, no
# implementation could ever fail it.
REFUSAL_LOG_MESSAGE = "revision guard refused the request"

# The step-2 cause. A cross-document probe against a real revision number must not
# look like an ordinary typo'd document id in the server's own records -- that is
# the one place the two are supposed to be distinguishable. Step 1's cause is
# shared with the edit guard and lives in `refusal_log_base`.
REVISION_SCOPE_REFUSAL_CAUSE = "revision-scope-refused"


class RevisionRefusalLogStatements(RevisionGuardBase, RefusalLogStatementsBase):
    """§1.3's instance of the refusal-log contract: the child id is the number."""

    logger_name = GUARD_LOGGER_NAME
    refusal_message = REFUSAL_LOG_MESSAGE
    child_id_field = "revision_number"
    child_scope_refusal_cause = REVISION_SCOPE_REFUSAL_CAUSE
    probe_description = "a real revision number"

    def __init__(self) -> None:
        # Both bases explicitly, rather than one cooperative `super()` chain: the
        # guard bases are plain arrangement classes that nothing else mixes into,
        # and an invisible chain through them is a worse trade than two lines here.
        RevisionGuardBase.__init__(self)
        RefusalLogStatementsBase.__init__(self)

    async def request_the_revision_under_the_second_document(self) -> None:
        await self.records_under_the_second_document()

    async def request_the_revision_under_an_absent_document(self) -> None:
        await self.records_under_an_absent_document()

    def assert_the_cross_document_record_omits_the_probed_number(self) -> None:
        self.assert_the_cross_document_record_omits_the_probed_child()
