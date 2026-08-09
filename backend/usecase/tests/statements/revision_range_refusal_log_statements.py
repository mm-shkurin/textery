"""What the range check records, and where it sits relative to the document guard.

`RevisionNumberRangeStatements` pins what an unusable revision number *answers*
the caller and that the store is never asked. Neither is affected by where the
parse sits: refusing before step 1 and refusing after it produce the same
canonical 404 with the same empty call log. The only observable that separates
the two orderings is the refusal record, so it is pinned here.

Two claims:

* An unusable number under the caller's own document is a step-2 refusal like any
  other -- the same cause, the same ids, and the probed number still absent.
* An unusable number aimed at a document the caller cannot resolve still emits the
  step-1 attribution record. Ordering the cheap parse first would let a caller
  suppress their own record by appending `/0/restore`.
"""

import logging
from uuid import UUID

from statements.document_guard_contract import ABSENT_DOCUMENT_ID, CALLER_ID
from statements.refusal_record_assertions import (
    ABSENT,
    DOCUMENT_SCOPE_REFUSAL_CAUSE,
    assert_record_ids,
    assert_record_shape,
)
from statements.refusal_record_shape_statements import (
    EXTRA_FIELDS_AT_STEP_ONE,
    EXTRA_FIELDS_AT_STEP_TWO,
    extra_field_names,
)
from statements.revision_number_range_statements import (
    NON_INTEGER_REVISION_NUMBERS,
    OUT_OF_RANGE_REVISION_NUMBERS,
)
from statements.revision_refusal_log_statements import (
    REVISION_SCOPE_REFUSAL_CAUSE,
    RevisionRefusalLogStatements,
)

# One probe of each unusable kind, taken from the rosters the range statements
# already own rather than written again here: the two files must probe the same
# values, and a second literal drifts the day one roster is extended.
OUT_OF_RANGE_PROBE = OUT_OF_RANGE_REVISION_NUMBERS[0]
NON_INTEGER_PROBE = NON_INTEGER_REVISION_NUMBERS[0]
UNUSABLE_PROBES = (OUT_OF_RANGE_PROBE, NON_INTEGER_PROBE)

FOREIGN_DOCUMENT_PATH = "the foreign document"
ABSENT_DOCUMENT_PATH = "the absent document"
UNRESOLVABLE_PATHS = (FOREIGN_DOCUMENT_PATH, ABSENT_DOCUMENT_PATH)


class RevisionRangeRefusalLogStatements(RevisionRefusalLogStatements):
    """The range check's cause, and its position behind the document guard."""

    def __init__(self) -> None:
        super().__init__()
        self._own_document_records: dict[str, list[logging.LogRecord]] = {}
        self._unresolvable_records: dict[str, list[logging.LogRecord]] = {}

    async def request_every_unusable_number_under_its_own_document(self) -> None:
        for probe in UNUSABLE_PROBES:
            self._own_document_records[probe] = await self._records_of_probe(
                self.first_document_id, probe
            )

    async def request_an_unusable_number_under_a_document_it_cannot_resolve(self) -> None:
        self._unresolvable_records[FOREIGN_DOCUMENT_PATH] = await self._records_of_probe(
            self.foreign_document_id, OUT_OF_RANGE_PROBE
        )
        self._unresolvable_records[ABSENT_DOCUMENT_PATH] = await self._records_of_probe(
            ABSENT_DOCUMENT_ID, OUT_OF_RANGE_PROBE
        )

    async def _records_of_probe(
        self, document_id: UUID, revision_number: str
    ) -> list[logging.LogRecord]:
        self._recorder.clear()
        await self.refusal_of(document_id, revision_number)
        return self._recorder.taken()

    def assert_every_unusable_number_refused_at_step_two(self) -> None:
        self._assert_roster(self._own_document_records, UNUSABLE_PROBES, "own-document")
        for probe in UNUSABLE_PROBES:
            record = self._only(self._own_document_records[probe], f"revision number '{probe}'")
            assert_record_shape(
                record,
                self.logger_name,
                self.refusal_message,
                REVISION_SCOPE_REFUSAL_CAUSE,
                f"revision number '{probe}'",
            )
            assert_record_ids(
                record,
                self.id_fields,
                {
                    "caller_id": str(CALLER_ID),
                    "document_id": str(self.first_document_id),
                    self.child_id_field: ABSENT,
                },
                f"revision number '{probe}'",
            )
            self._assert_whole_extra_set(
                record, EXTRA_FIELDS_AT_STEP_TWO, f"revision number '{probe}'"
            )

    def assert_an_unresolvable_document_still_records_the_attribution(self) -> None:
        """The load-bearing one: the parse must not run ahead of the document guard.

        Both orderings answer the caller the identical canonical 404 and leave the
        revision store untouched, so nothing else in this suite can tell them
        apart. If the parse ran first, `0` would short-circuit before step 1 ever
        looked the document up, and a caller enumerating document ids could switch
        the attribution channel off for themselves by appending `/0/restore` --
        exactly the ids the step-1 cause exists to record.
        """
        self._assert_roster(self._unresolvable_records, UNRESOLVABLE_PATHS, "unresolvable-document")
        for which in UNRESOLVABLE_PATHS:
            record = self._only(self._unresolvable_records[which], which)
            assert_record_shape(
                record,
                self.logger_name,
                self.refusal_message,
                DOCUMENT_SCOPE_REFUSAL_CAUSE,
                which,
            )
            assert_record_ids(
                record,
                self.id_fields,
                {
                    "caller_id": str(CALLER_ID),
                    "document_id": ABSENT,
                    self.child_id_field: ABSENT,
                },
                which,
            )
            self._assert_whole_extra_set(record, EXTRA_FIELDS_AT_STEP_ONE, which)

    def assert_the_revision_store_was_never_asked(self) -> None:
        self._assert_revision_lookups(
            [],
            "every probe here is unusable, so the guard must refuse it itself -- and the "
            "unresolvable-document probes must not reach the store at all",
        )

    def _assert_whole_extra_set(
        self, record: logging.LogRecord, expected: frozenset[str], which: str
    ) -> None:
        """The extras as a whole set, not field by field.

        `assert_record_ids` reads through a pinned roster, so a field nobody
        enumerated -- the probed number arriving under some new name, an ip, an
        owner id -- is invisible to it. Subtracting the standard `LogRecord`
        attributes and comparing what is left is the story's whole-set rule, reused
        from `refusal_record_shape_statements` rather than restated.
        """
        actual = extra_field_names(record)
        assert actual == expected, (
            f"the {which} refusal record attached the extras {sorted(actual)}, expected "
            f"{sorted(expected)} -- a field outside the enumerated roster passes every "
            f"id check while carrying something the caller proved no claim to"
        )

    def _assert_roster(
        self, collected: dict[str, list[logging.LogRecord]], expected: tuple[str, ...], which: str
    ) -> None:
        assert tuple(collected) == expected, (
            f"the {which} probe covered {tuple(collected)}, expected {expected} -- a roster "
            f"read back off the act step agrees with any subset of itself"
        )

    def _only(self, records: list[logging.LogRecord], which: str) -> logging.LogRecord:
        assert len(records) == 1, (
            f"the {which} refusal emitted {len(records)} records on '{self.logger_name}', "
            f"expected exactly one: {[record.getMessage() for record in records]} -- a refusal "
            f"nobody records is a probe nobody can attribute"
        )
        return records[0]
