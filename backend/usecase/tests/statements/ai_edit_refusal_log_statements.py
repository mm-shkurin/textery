import logging
from uuid import UUID

from statements.ai_edit_guard_base import (
    ABSENT_DOCUMENT_ID,
    CALLER_ID,
    AiEditGuardBase,
)
from statements.arranged import arranged

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
ID_FIELDS = ("caller_id", "document_id", "edit_id")
_ABSENT = "<absent>"


class _RecordingHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


class AiEditRefusalLogStatements(AiEditGuardBase):
    """Client-indistinguishable, server-attributable.

    Both refusals are byte-identical to the caller, which is the point -- and
    which is exactly why the server must be able to tell them apart. A refusal at
    step 2 means the caller held a real edit id and asked for it under a document
    they own; that is a probe, and without its own record it is invisible.
    """

    def __init__(self) -> None:
        super().__init__()
        self._handler = _RecordingHandler()
        self._logger = logging.getLogger(GUARD_LOGGER_NAME)
        self._previous_level: int | None = None
        self._cross_document_records: list[logging.LogRecord] | None = None
        self._absent_document_records: list[logging.LogRecord] | None = None

    def given_the_guards_own_log_is_collected(self) -> None:
        self._previous_level = self._logger.level
        self._logger.addHandler(self._handler)
        self._logger.setLevel(logging.INFO)

    def stop_collecting(self) -> None:
        """Undo *both* mutations, so one test's collector cannot outlive its test.

        Removing the handler but leaving `setLevel(INFO)` in place would keep a
        process-global change to a module logger for every later test in the run.
        """
        self._logger.removeHandler(self._handler)
        if self._previous_level is not None:
            self._logger.setLevel(self._previous_level)
        self._handler.close()

    async def request_the_edit_under_the_second_document(self) -> None:
        self._cross_document_records = await self._records_of(self.second_document_id)

    async def request_the_edit_under_an_absent_document(self) -> None:
        self._absent_document_records = await self._records_of(ABSENT_DOCUMENT_ID)

    async def _records_of(self, document_id: UUID) -> list[logging.LogRecord]:
        self._handler.records.clear()
        await self.refusal_of(document_id)
        return list(self._handler.records)

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
        record = self._cross_document_record()
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
        record = self._absent_document_record()
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
        no implementation could ever fail. What has to hold is that the guard
        stamped *different* causes on the two refusals -- a single shared cause,
        or a record carrying both, makes the probe unattributable.
        """
        cross = getattr(self._cross_document_record(), "refusal_cause", _ABSENT)
        absent = getattr(self._absent_document_record(), "refusal_cause", _ABSENT)
        assert cross != absent, (
            f"both refusals were recorded under the cause '{cross}' -- a cross-document probe "
            f"against a real edit id is then indistinguishable from a typo'd document id in "
            f"our own records, which is the one place the two must be told apart"
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
        actual = {name: getattr(record, name, _ABSENT) for name in ID_FIELDS}
        assert actual == expected, (
            f"the {which} refusal record carries ids {actual}, expected {expected} -- an id "
            f"the caller has no proven claim to must not be written to our logs, and the ids "
            f"they do own must be there for the record to be attributable"
        )

    def _cross_document_record(self) -> logging.LogRecord:
        return self._first(
            arranged(self._cross_document_records, "cross_document_records"), "cross-document"
        )

    def _absent_document_record(self) -> logging.LogRecord:
        return self._first(
            arranged(self._absent_document_records, "absent_document_records"), "absent-document"
        )

    def _first(self, records: list[logging.LogRecord], which: str) -> logging.LogRecord:
        assert records, (
            f"the {which} refusal emitted no record on '{GUARD_LOGGER_NAME}' at all -- a "
            f"refusal nobody records is a probe nobody can attribute"
        )
        return records[0]

    def _collected(self) -> list[tuple[list[logging.LogRecord], str]]:
        return [
            (arranged(self._cross_document_records, "cross_document_records"), "cross-document"),
            (arranged(self._absent_document_records, "absent_document_records"), "absent-document"),
        ]
