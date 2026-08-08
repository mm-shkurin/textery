"""Collecting the refusal records both child-scope guards emit.

§1.2 (`ai_edit_refusal_log_statements`) and §1.3 (`revision_refusal_log_statements`)
grew as near-total copies: the same recorder wiring, the same two act steps, the
same record accessors, the same cardinality guard. What genuinely differs between
them is data, not behaviour -- the logger, the message literal, the name of the
child id, the step-2 cause -- so those are class attributes and everything else is
written once here.

Judging a record once it is in hand is the other half, and it lives in
`refusal_record_assertions`; this class only gets hold of one.
"""

import logging
from uuid import UUID

from shared.exceptions import NotFoundException
from statements.arranged import arranged
from statements.document_guard_contract import ABSENT_DOCUMENT_ID, CALLER_ID
from statements.log_recorder import RecordingLogger
from statements.refusal_record_assertions import (
    ABSENT,
    DOCUMENT_SCOPE_REFUSAL_CAUSE,
    assert_causes_are_distinct,
    assert_record_ids,
    assert_record_shape,
)


class RefusalLogStatementsBase:
    """Client-indistinguishable, server-attributable.

    Both refusals are byte-identical to the caller, which is the point, and which
    is exactly why the server must be able to tell them apart. A refusal at step 2
    means the caller held a real child identifier and asked for it under a document
    they own; that is a probe, and without its own cause it is invisible.
    """

    logger_name: str
    refusal_message: str
    child_id_field: str
    child_scope_refusal_cause: str
    # How the step-2 probe reads in a failure message ("a real edit id").
    probe_description: str

    def __init__(self) -> None:
        self._recorder = RecordingLogger(self.logger_name)
        self._cross_document_records: list[logging.LogRecord] | None = None
        self._absent_document_records: list[logging.LogRecord] | None = None

    @property
    def id_fields(self) -> tuple[str, ...]:
        """Every id-bearing field the guard may attach, enumerated so a record can
        be asserted as a whole mapping rather than field by field."""
        return ("caller_id", "document_id", self.child_id_field)

    # -- arrangement supplied by the guard base this class is mixed into --------

    @property
    def second_document_id(self) -> UUID:
        raise NotImplementedError

    async def refusal_of(self, document_id: UUID) -> NotFoundException:
        raise NotImplementedError

    # -- collection ------------------------------------------------------------

    def given_the_guards_own_log_is_collected(self) -> None:
        self._recorder.start()

    def stop_collecting(self) -> None:
        self._recorder.stop()

    async def records_under_the_second_document(self) -> None:
        self._cross_document_records = await self._records_of(self.second_document_id)

    async def records_under_an_absent_document(self) -> None:
        self._absent_document_records = await self._records_of(ABSENT_DOCUMENT_ID)

    async def _records_of(self, document_id: UUID) -> list[logging.LogRecord]:
        self._recorder.clear()
        await self.refusal_of(document_id)
        return self._recorder.taken()

    # -- assertions ------------------------------------------------------------

    def assert_each_refusal_emitted_exactly_one_record(self) -> None:
        """Cardinality, in the then-phase where a reader can see it.

        This used to fire inside the act step, which made a real behavioural
        contract -- one record per refusal, never zero and never a duplicate pair
        that would double-count a probe -- invisible in the test body.
        """
        for records, which in self._collected():
            assert len(records) == 1, (
                f"expected exactly one record on '{self.logger_name}' for the {which} refusal, "
                f"got {len(records)}: {[record.getMessage() for record in records]}"
            )

    def assert_the_cross_document_record_omits_the_probed_child(self) -> None:
        record = self.cross_document_record()
        assert_record_shape(
            record,
            self.logger_name,
            self.refusal_message,
            self.child_scope_refusal_cause,
            "cross-document",
        )
        assert_record_ids(
            record,
            self.id_fields,
            {
                "caller_id": str(CALLER_ID),
                "document_id": str(self.second_document_id),
                self.child_id_field: ABSENT,
            },
            "cross-document",
        )

    def assert_the_absent_document_record_has_the_other_cause(self) -> None:
        record = self.absent_document_record()
        assert_record_shape(
            record,
            self.logger_name,
            self.refusal_message,
            DOCUMENT_SCOPE_REFUSAL_CAUSE,
            "absent-document",
        )
        assert_record_ids(
            record,
            self.id_fields,
            # `caller_id` is the one id step 1 legitimately knows, and pinning it is
            # what stops the two absences from passing on an empty record. It is also
            # what makes the cause attributable at all -- "id-free" means the message
            # and the peer ids, never the caller's own id.
            {"caller_id": str(CALLER_ID), "document_id": ABSENT, self.child_id_field: ABSENT},
            "absent-document",
        )

    def assert_the_two_causes_are_distinct(self) -> None:
        assert_causes_are_distinct(
            self.cross_document_record(),
            self.absent_document_record(),
            self.child_scope_refusal_cause,
            self.probe_description,
        )

    # -- record accessors ------------------------------------------------------

    def cross_document_record(self) -> logging.LogRecord:
        return self._first(
            arranged(self._cross_document_records, "cross_document_records"), "cross-document"
        )

    def absent_document_record(self) -> logging.LogRecord:
        return self._first(
            arranged(self._absent_document_records, "absent_document_records"), "absent-document"
        )

    def _first(self, records: list[logging.LogRecord], which: str) -> logging.LogRecord:
        """The one record, with the cardinality pinned rather than merely non-empty.

        `assert records` was a truthiness check on a collection whose size is fully
        determined -- exactly one record per refusal. That was not just loose, it was
        a hole: `refusal_record_shape_statements` reaches these accessors without ever
        calling `assert_each_refusal_emitted_exactly_one_record`, so on that test path
        a guard emitting a duplicate pair -- which double-counts a probe in the one
        channel built to attribute probes -- passed while only `records[0]` was ever
        inspected.
        """
        assert len(records) == 1, (
            f"the {which} refusal emitted {len(records)} records on '{self.logger_name}', "
            f"expected exactly one: {[record.getMessage() for record in records]} -- a refusal "
            f"nobody records is a probe nobody can attribute, and one recorded twice is a probe "
            f"counted twice"
        )
        return records[0]

    def _collected(self) -> list[tuple[list[logging.LogRecord], str]]:
        return [
            (arranged(self._cross_document_records, "cross_document_records"), "cross-document"),
            (arranged(self._absent_document_records, "absent_document_records"), "absent-document"),
        ]
