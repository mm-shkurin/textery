import logging
from uuid import UUID

from statements.arranged import arranged
from statements.document_guard_contract import ABSENT_DOCUMENT_ID, CALLER_ID
from statements.log_recorder import RecordingLogger
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

# The two cause discriminators. A cross-document probe against a real revision
# number must not look like an ordinary typo'd document id in the server's own
# records -- that is the one place the two are supposed to be distinguishable.
DOCUMENT_SCOPE_REFUSAL_CAUSE = "document-scope-refused"
REVISION_SCOPE_REFUSAL_CAUSE = "revision-scope-refused"

# Every id-bearing field the guard is allowed to attach, enumerated so each record
# can be asserted as a whole mapping. A field the guard must not carry is expected
# to be `_ABSENT`, which makes "the guard recorded nothing" fail the same assertion
# that pins the ids it *must* carry -- a bare `not hasattr` is satisfied by a record
# with no fields at all.
REVISION_ID_FIELDS = ("caller_id", "document_id", "revision_number")
ABSENT = "<absent>"


class RevisionRefusalLogStatements(RevisionGuardBase):
    """Client-indistinguishable, server-attributable.

    Both refusals are byte-identical to the caller, which is the point, and which
    is exactly why the server must be able to tell them apart. A refusal at step 2
    means the caller held a real revision number and asked for it under a document
    they own; that is a probe, and without its own cause it is invisible.
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

    async def request_the_revision_under_the_second_document(self) -> None:
        self._cross_document_records = await self._records_of(self.second_document_id)

    async def request_the_revision_under_an_absent_document(self) -> None:
        self._absent_document_records = await self._records_of(ABSENT_DOCUMENT_ID)

    def assert_each_refusal_emitted_exactly_one_record(self) -> None:
        for records, which in self._collected():
            assert len(records) == 1, (
                f"expected exactly one record on '{GUARD_LOGGER_NAME}' for the {which} refusal, "
                f"got {len(records)}: {[record.getMessage() for record in records]}"
            )

    def assert_the_cross_document_record_omits_the_probed_number(self) -> None:
        record = self.cross_document_record()
        self._assert_shape(record, REVISION_SCOPE_REFUSAL_CAUSE, "cross-document")
        self._assert_ids(
            record,
            {
                "caller_id": str(CALLER_ID),
                "document_id": str(self.second_document_id),
                "revision_number": ABSENT,
            },
            "cross-document",
        )

    def assert_the_absent_document_record_has_the_other_cause(self) -> None:
        record = self.absent_document_record()
        self._assert_shape(record, DOCUMENT_SCOPE_REFUSAL_CAUSE, "absent-document")
        self._assert_ids(
            record,
            # `caller_id` is the one id step 1 legitimately knows, and pinning it is
            # what stops the two absences below from passing on an empty record. It
            # is also what makes the cause attributable at all -- "id-free" means the
            # message and the peer ids, never the caller's own id.
            {"caller_id": str(CALLER_ID), "document_id": ABSENT, "revision_number": ABSENT},
            "absent-document",
        )

    def assert_the_two_causes_are_distinct(self) -> None:
        """Both operands read off production records, and both pinned exactly.

        Comparing the two module constants to each other is something no
        implementation can fail. Comparing the two *records* for inequality is
        better but still relative: a guard that stamped some third pair of
        different-but-wrong causes satisfies `!=` while the two values operators
        actually alert on have silently moved. Pinned as one tuple equality, so
        the property is both "different" and "these two".
        """
        cross = getattr(self.cross_document_record(), "refusal_cause", ABSENT)
        absent = getattr(self.absent_document_record(), "refusal_cause", ABSENT)
        expected = (REVISION_SCOPE_REFUSAL_CAUSE, DOCUMENT_SCOPE_REFUSAL_CAUSE)
        assert (cross, absent) == expected, (
            f"the two refusals were recorded under the causes {(cross, absent)}, expected "
            f"{expected} -- a cross-document probe against a real revision number must not be "
            f"indistinguishable from a typo'd document id in our own records, which is the one "
            f"place the two must be told apart"
        )

    def cross_document_record(self) -> logging.LogRecord:
        return _first(
            arranged(self._cross_document_records, "cross_document_records"), "cross-document"
        )

    def absent_document_record(self) -> logging.LogRecord:
        return _first(
            arranged(self._absent_document_records, "absent_document_records"), "absent-document"
        )

    async def _records_of(self, document_id: UUID) -> list[logging.LogRecord]:
        self._recorder.clear()
        await self.refusal_of(document_id)
        return self._recorder.taken()

    def _assert_shape(self, record: logging.LogRecord, cause: str, which: str) -> None:
        actual = (
            record.name,
            record.levelno,
            record.getMessage(),
            getattr(record, "refusal_cause", ABSENT),
        )
        expected = (GUARD_LOGGER_NAME, logging.INFO, REFUSAL_LOG_MESSAGE, cause)
        assert actual == expected, (
            f"the {which} refusal record is {actual}, expected {expected} -- the line must be "
            f"the id-free literal at INFO on the guard's own logger, discriminated only by its "
            f"structured cause"
        )

    def _assert_ids(self, record: logging.LogRecord, expected: dict[str, str], which: str) -> None:
        actual = {name: getattr(record, name, ABSENT) for name in REVISION_ID_FIELDS}
        assert actual == expected, (
            f"the {which} refusal record carries ids {actual}, expected {expected} -- an id the "
            f"caller has no proven claim to must not be written to our logs, and the ids they "
            f"do own must be there for the record to be attributable"
        )

    def _collected(self) -> list[tuple[list[logging.LogRecord], str]]:
        return [
            (arranged(self._cross_document_records, "cross_document_records"), "cross-document"),
            (arranged(self._absent_document_records, "absent_document_records"), "absent-document"),
        ]


def _first(records: list[logging.LogRecord], which: str) -> logging.LogRecord:
    """The one record, with the cardinality pinned rather than merely non-empty.

    `assert records` was a truthiness check on a collection whose size is fully
    determined -- exactly one record per refusal. That was not just loose, it was
    a hole: `refusal_record_shape_statements` reaches the record accessors without
    ever calling `assert_each_refusal_emitted_exactly_one_record`, so on that test
    path a guard emitting a duplicate pair -- which double-counts a probe in the
    one channel built to attribute probes -- passed while only `records[0]` was
    ever inspected.
    """
    assert len(records) == 1, (
        f"the {which} refusal emitted {len(records)} records on '{GUARD_LOGGER_NAME}', expected "
        f"exactly one: {[record.getMessage() for record in records]} -- a refusal nobody records "
        f"is a probe nobody can attribute, and one recorded twice is a probe counted twice"
    )
    return records[0]
