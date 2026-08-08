import logging
from uuid import UUID

from statements.ai_edit_guard_base import AiEditGuardBase
from statements.arranged import arranged
from statements.document_guard_contract import ABSENT_DOCUMENT_ID, CALLER_ID
from statements.log_recorder import RecordingLogger

# The logger the guard emits under. Pinned as a literal so the record cannot be
# moved to a logger nobody collects and stay green.
GUARD_LOGGER_NAME = "document_edit.resolve_owned_edit"

# The one refusal line, identical for both causes and carrying no ids at all.
# Asserted with `==` rather than `in`: a substring check leaves the rest of the
# message unconstrained, so an id the guard was never supposed to record could
# ride along in text while every `not in` check for the *enumerated* ids passed.
# Everything that varies between the two refusals lives in structured fields
# below, where it can be asserted exactly and, more importantly, asserted absent.
REFUSAL_LOG_MESSAGE = "ai edit guard refused the request"

# The two cause discriminators. A cross-document probe against a real, harvested
# edit id must not look like an ordinary typo'd document id in the server's own
# records -- which is the one place the two are supposed to be distinguishable.
DOCUMENT_SCOPE_REFUSAL_CAUSE = "document-scope-refused"
EDIT_SCOPE_REFUSAL_CAUSE = "edit-scope-refused"

# Every id-bearing field the guard is allowed to attach, enumerated so each
# record can be asserted as a whole mapping. An id that failed to resolve is
# expected to be `_ABSENT`, which makes "the guard recorded nothing" fail the
# same assertion that pins the ids it *must* carry -- a bare `not hasattr` would
# be satisfied by a record with no fields at all.
EDIT_ID_FIELDS = ("caller_id", "document_id", "edit_id")
_ABSENT = "<absent>"


class AiEditRefusalLogStatements(AiEditGuardBase):
    """Client-indistinguishable, server-attributable.

    Both refusals are byte-identical to the caller, which is the point -- and
    which is exactly why the server must be able to tell them apart. A refusal at
    step 2 means the caller held a real edit id and asked for it under a document
    they own; that is a probe, and without its own record it is invisible.
    """

    def __init__(self) -> None:
        super().__init__()
        self._recorder = RecordingLogger(GUARD_LOGGER_NAME)
        self._cross_document_records: list[logging.LogRecord] | None = None
        self._absent_document_records: list[logging.LogRecord] | None = None

    def given_the_guards_own_log_is_collected(self) -> None:
        self._recorder.start()

    def stop_collecting(self) -> None:
        self._recorder.stop()

    async def request_the_edit_under_the_second_document(self) -> None:
        self._cross_document_records = await self._records_of(self.second_document_id)

    async def request_the_edit_under_an_absent_document(self) -> None:
        self._absent_document_records = await self._records_of(ABSENT_DOCUMENT_ID)

    async def _records_of(self, document_id: UUID) -> list[logging.LogRecord]:
        self._recorder.clear()
        await self.refusal_of(document_id)
        return self._recorder.taken()

    def assert_each_refusal_emitted_exactly_one_record(self) -> None:
        """Cardinality, in the then-phase where a reader can see it.

        This used to fire inside the act step, which made a real behavioural
        contract -- one record per refusal, never zero and never a duplicate pair
        that would double-count a probe -- invisible in the test body.
        """
        for records, which in self._collected():
            assert len(records) == 1, (
                f"expected exactly one record on '{GUARD_LOGGER_NAME}' for the {which} "
                f"refusal, got {len(records)}: {[record.getMessage() for record in records]}"
            )

    def assert_the_cross_document_record_omits_the_probed_id(self) -> None:
        record = self.cross_document_record()
        self._assert_shape(record, EDIT_SCOPE_REFUSAL_CAUSE, "cross-document")
        self._assert_ids(
            record,
            {
                "caller_id": str(CALLER_ID),
                "document_id": str(self.second_document_id),
                "edit_id": _ABSENT,
            },
            "cross-document",
        )

    def assert_the_absent_document_record_has_the_other_cause(self) -> None:
        record = self.absent_document_record()
        self._assert_shape(record, DOCUMENT_SCOPE_REFUSAL_CAUSE, "absent-document")
        self._assert_ids(
            record,
            # The caller id is the one id step 1 legitimately knows, and pinning it
            # is what stops the two absences below from passing on an empty record.
            {"caller_id": str(CALLER_ID), "document_id": _ABSENT, "edit_id": _ABSENT},
            "absent-document",
        )

    def assert_the_two_causes_are_distinct(self) -> None:
        """Both operands read off production records, not off this file.

        The previous form compared the two module constants to each other, which
        no implementation could ever fail. Comparing the two records for mere
        inequality was the next form and is still relative: a guard that stamped
        some third pair of different-but-wrong causes satisfies `!=` while the two
        values operators actually alert on have silently moved. Pinned as one
        tuple equality, so the property is both "different" and "these two".
        """
        cross = getattr(self.cross_document_record(), "refusal_cause", _ABSENT)
        absent = getattr(self.absent_document_record(), "refusal_cause", _ABSENT)
        expected = (EDIT_SCOPE_REFUSAL_CAUSE, DOCUMENT_SCOPE_REFUSAL_CAUSE)
        assert (cross, absent) == expected, (
            f"the two refusals were recorded under the causes {(cross, absent)}, expected "
            f"{expected} -- a cross-document probe against a real edit id must not be "
            f"indistinguishable from a typo'd document id in our own records, which is the "
            f"one place the two must be told apart"
        )

    def _assert_shape(self, record: logging.LogRecord, cause: str, which: str) -> None:
        actual = (
            record.name,
            record.levelno,
            record.getMessage(),
            getattr(record, "refusal_cause", _ABSENT),
        )
        expected = (GUARD_LOGGER_NAME, logging.INFO, REFUSAL_LOG_MESSAGE, cause)
        assert actual == expected, (
            f"the {which} refusal record is {actual}, expected {expected} -- the line must be "
            f"the id-free literal at INFO on the guard's own logger, discriminated only by "
            f"its structured cause"
        )

    def _assert_ids(self, record: logging.LogRecord, expected: dict[str, str], which: str) -> None:
        actual = {name: getattr(record, name, _ABSENT) for name in EDIT_ID_FIELDS}
        assert actual == expected, (
            f"the {which} refusal record carries ids {actual}, expected {expected} -- an id "
            f"the caller has no proven claim to must not be written to our logs, and the ids "
            f"they do own must be there for the record to be attributable"
        )

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

        `assert records` was a truthiness check on a collection whose size is
        fully determined. 1.3's `refusal_record_shape_statements` now reaches
        these accessors without calling
        `assert_each_refusal_emitted_exactly_one_record`, so on that path a guard
        emitting a duplicate pair passed while only `records[0]` was inspected.
        """
        assert len(records) == 1, (
            f"the {which} refusal emitted {len(records)} records on '{GUARD_LOGGER_NAME}', "
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
