from statements.ai_edit_guard_base import AiEditGuardBase
from statements.refusal_log_base import RefusalLogStatementsBase

# The logger the guard emits under, pinned as a literal so the record cannot be
# moved to a logger nobody collects and stay green.
GUARD_LOGGER_NAME = "document_edit.resolve_owned_edit"

# The one refusal line, identical for both causes and carrying no ids at all.
# Asserted with `==` rather than `in`: a substring check leaves the rest of the
# message unconstrained, so an id the guard was never supposed to record could ride
# along in text while every check for the *enumerated* ids passed. Everything that
# varies between the two refusals lives in structured fields, where it can be
# asserted exactly and, more importantly, asserted absent.
REFUSAL_LOG_MESSAGE = "ai edit guard refused the request"

# The step-2 cause. A cross-document probe against a real, harvested edit id must
# not look like an ordinary typo'd document id in the server's own records -- that
# is the one place the two are supposed to be distinguishable. Step 1's cause is
# shared with the revision guard and lives in `refusal_log_base`.
EDIT_SCOPE_REFUSAL_CAUSE = "edit-scope-refused"


class AiEditRefusalLogStatements(AiEditGuardBase, RefusalLogStatementsBase):
    """§1.2's instance of the refusal-log contract: the child id is the edit id."""

    logger_name = GUARD_LOGGER_NAME
    refusal_message = REFUSAL_LOG_MESSAGE
    child_id_field = "edit_id"
    child_scope_refusal_cause = EDIT_SCOPE_REFUSAL_CAUSE
    probe_description = "a real edit id"

    def __init__(self) -> None:
        # Both bases explicitly, rather than one cooperative `super()` chain: the
        # guard bases are plain arrangement classes that nothing else mixes into,
        # and an invisible chain through them is a worse trade than two lines here.
        AiEditGuardBase.__init__(self)
        RefusalLogStatementsBase.__init__(self)

    async def request_the_edit_under_the_second_document(self) -> None:
        await self.records_under_the_second_document()

    async def request_the_edit_under_an_absent_document(self) -> None:
        await self.records_under_an_absent_document()

    def assert_the_cross_document_record_omits_the_probed_id(self) -> None:
        self.assert_the_cross_document_record_omits_the_probed_child()
