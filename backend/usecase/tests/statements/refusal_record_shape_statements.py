import logging

from statements.ai_edit_refusal_log_statements import AiEditRefusalLogStatements
from statements.document_guard_contract import CALLER_ID
from statements.revision_refusal_log_statements import RevisionRefusalLogStatements

# What `logging` itself puts on every record, sampled from a bare `LogRecord` plus
# the two names a formatter injects. Read off the logging library -- which is not
# the thing under test -- so the scan below is "everything the guard attached" with
# nothing enumerated by hand, and it does not rot when a Python release adds an
# attribute (`taskName` arrived in 3.12).
_STANDARD_RECORD_ATTRIBUTES = frozenset(
    logging.LogRecord("", logging.INFO, "", 0, "", None, None).__dict__
) | {"message", "asctime"}

# What each step is allowed to have attached, as the WHOLE extra set, pinned
# absolutely.
#
# This used to be scanned through a roster unioned from the two guards' own
# `*_ID_FIELDS` tuples -- a roster derived from the very thing it guards. Those
# tuples are test-side literals that do not move when a guard grows a field, so a
# guard attaching `owner_id`, `probe_ip` or a renamed peer id was invisible to the
# scan: both sides yielded the same filtered set and this class stayed green on
# precisely the drift it advertises. The extras are now read off the record itself
# and compared whole, so an unenumerated field fails here rather than hiding.
#
# `refusal_cause` is expected rather than filtered out: an exclusion list is the
# same hand-maintained roster in negative form.
EXTRA_FIELDS_AT_STEP_ONE = frozenset({"refusal_cause", "caller_id"})
EXTRA_FIELDS_AT_STEP_TWO = frozenset({"refusal_cause", "caller_id", "document_id"})


def _extra_field_names(record: logging.LogRecord) -> frozenset[str]:
    """Every field the guard attached, and nothing the logging library added."""
    return frozenset(record.__dict__) - _STANDARD_RECORD_ATTRIBUTES


class RefusalRecordShapeStatements:
    """The two guards must build their `extra` fields by the same rule.

    The ADR requires `_log_refusal` to be *shared* with `resolve_owned_edit`
    rather than copied, and the reason is a rule that is easy to state and easy to
    half-copy: always carry the caller's own id, never carry the peer id the
    caller failed to prove a claim to. A second hand-written `extra` dict drifts on
    exactly that distinction -- and it drifts silently, because each guard's own
    tests pin only its own literals and both stay green.

    So the property is asserted *between* the guards, with both sides read off
    emitted records. Neither side is a literal in this file: a rule both guards
    moved away from together would still fail here only if the move made them
    disagree, which is the honest scope of a shared-shape test, and it is what a
    copy-paste divergence actually looks like.

    Composed of the two log Statements rather than delegating to them: every
    method here reads both and compares, which is the work. A method that only
    forwarded to one of them would be the middleman the house rules forbid.
    """

    def __init__(
        self,
        edit_statements: AiEditRefusalLogStatements,
        revision_statements: RevisionRefusalLogStatements,
    ) -> None:
        self.edit = edit_statements
        self.revision = revision_statements

    async def given_both_guards_have_refused_at_both_steps(self) -> None:
        await self.edit.given_the_caller_owns_two_documents()
        self.edit.given_an_edit_queued_on_the_first_document()
        self.edit.given_the_guards_own_log_is_collected()
        await self.edit.request_the_edit_under_the_second_document()
        await self.edit.request_the_edit_under_an_absent_document()

        await self.revision.given_the_caller_owns_two_documents()
        self.revision.given_a_revision_recorded_on_the_first_document()
        self.revision.given_the_guards_own_log_is_collected()
        await self.revision.request_the_revision_under_the_second_document()
        await self.revision.request_the_revision_under_an_absent_document()

    def assert_both_guards_record_the_same_id_fields(self) -> None:
        """Each side pinned to its literal set first, then compared to the other.

        The cross-guard equality alone is relative, and it fails open in the worst
        direction: two guards that attached no `extra` at all produce two empty
        sets and agree perfectly. The literal expectation is what makes "the same"
        mean the right shape rather than merely a shared one; the equality that
        follows is still worth keeping, because it is the drift this class is for.

        Both operands are the records' whole extra sets, so a field either guard
        grew that nobody enumerated widens one side and fails here.
        """
        for which, expected, edit_record, revision_record in self._paired():
            edit_fields = _extra_field_names(edit_record)
            revision_fields = _extra_field_names(revision_record)
            assert (edit_fields, revision_fields) == (expected, expected), (
                f"at {which} the edit guard attached the fields {sorted(edit_fields)} and "
                f"the revision guard attached {sorted(revision_fields)}, expected both to be "
                f"{sorted(expected)} -- the two must build their `extra` by one shared rule "
                f"(always the caller's own id, never a peer id the caller has not proven a "
                f"claim to), and two hand-written dicts drift on exactly this distinction "
                f"while each guard's own tests stay green"
            )

    def assert_the_caller_is_attributable_at_both_steps(self) -> None:
        """The half of the rule a literal reading of "id-free" would destroy.

        "Step-1 cause id-free" means the message and the peer id, never the
        caller's own id -- taken at face value it would make step-1 refusals
        anonymous in the one channel built to attribute them.

        Asserted as the exact caller id rather than `hasattr`: the value is fully
        determined here, and a presence check is satisfied by a field carrying the
        wrong account -- which is worse than an absent one, because it attributes
        a probe to somebody who did not make it.
        """
        expected = str(CALLER_ID)
        for which, _, edit_record, revision_record in self._paired():
            actual = (
                getattr(edit_record, "caller_id", None),
                getattr(revision_record, "caller_id", None),
            )
            assert actual == (expected, expected), (
                f"at {which} the edit and revision guards recorded the caller ids {actual}, "
                f"expected both to be '{expected}' -- a refusal nobody can attribute to an "
                f"account is a probe nobody can act on, and one attributed to the wrong "
                f"account is worse"
            )

    def _paired(
        self,
    ) -> list[tuple[str, frozenset[str], logging.LogRecord, logging.LogRecord]]:
        return [
            (
                "step 1",
                EXTRA_FIELDS_AT_STEP_ONE,
                self.edit.absent_document_record(),
                self.revision.absent_document_record(),
            ),
            (
                "step 2",
                EXTRA_FIELDS_AT_STEP_TWO,
                self.edit.cross_document_record(),
                self.revision.cross_document_record(),
            ),
        ]
