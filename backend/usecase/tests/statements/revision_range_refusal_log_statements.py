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

from statements.document_guard_contract import (
    ABSENT_DOCUMENT_ID,
    CALLER_ID,
    assert_is_the_canonical_refusal,
    outcome_of,
)
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

# Every unusable value, both kinds, taken whole from the rosters the range
# statements already own. This was `roster[0]` of each, which pinned one value per
# kind and changed which ones the day either roster was reordered. The per-probe
# assertion is value-independent, so walking both entire costs nothing.
UNUSABLE_PROBES = OUT_OF_RANGE_REVISION_NUMBERS + NON_INTEGER_REVISION_NUMBERS

FOREIGN_DOCUMENT_PATH = "the foreign document"
ABSENT_DOCUMENT_PATH = "the absent document"
UNRESOLVABLE_PATHS = (FOREIGN_DOCUMENT_PATH, ABSENT_DOCUMENT_PATH)

# Both unresolvable documents crossed with both parse branches. An `int()`
# conversion ordered ahead of step 1 suppresses the attribution record exactly as
# a range check does, so probing only the range branch would leave `/abc/restore`
# as an unpinned way to switch the channel off.
UNRESOLVABLE_CASES = tuple(
    (path, probe) for path in UNRESOLVABLE_PATHS for probe in UNUSABLE_PROBES
)

# What the act steps record per probe: what the guard raised, and what it logged.
Probed = tuple[object, list[logging.LogRecord]]


class RevisionRangeRefusalLogStatements(RevisionRefusalLogStatements):
    """The range check's cause, and its position behind the document guard."""

    def __init__(self) -> None:
        super().__init__()
        self._own_document: dict[str, Probed] = {}
        self._unresolvable: dict[tuple[str, str], Probed] = {}

    async def request_every_unusable_number_under_its_own_document(self) -> None:
        for probe in UNUSABLE_PROBES:
            self._own_document[probe] = await self._probe(self.first_document_id, probe)

    async def request_an_unusable_number_under_a_document_it_cannot_resolve(self) -> None:
        for path, document_id in (
            (FOREIGN_DOCUMENT_PATH, self.foreign_document_id),
            (ABSENT_DOCUMENT_PATH, ABSENT_DOCUMENT_ID),
        ):
            for probe in UNUSABLE_PROBES:
                self._unresolvable[(path, probe)] = await self._probe(document_id, probe)

    async def _probe(self, document_id: UUID, revision_number: str) -> Probed:
        """Records what came back and what was logged; judges neither.

        `outcome_of` rather than `refusal_of`: the latter runs through `captured`,
        which enforces the exception type and fails when the guard returns instead
        of refusing -- a real contract applied from inside the act half, where no
        reader of the test body can see it. The judging is in the then-phase.
        """
        self._recorder.clear()
        outcome = await outcome_of(self.resolve(document_id, revision_number))
        return outcome, self._recorder.taken()

    def assert_every_unusable_number_was_the_canonical_refusal(self) -> None:
        for probe in UNUSABLE_PROBES:
            outcome, _ = self._own_document[probe]
            assert_is_the_canonical_refusal(outcome, f"revision number '{probe}'")

    def assert_every_unusable_number_refused_at_step_two(self) -> None:
        for probe in UNUSABLE_PROBES:
            which = f"revision number '{probe}'"
            record = self._first(self._own_document[probe][1], which)
            assert_record_shape(
                record,
                self.logger_name,
                self.refusal_message,
                REVISION_SCOPE_REFUSAL_CAUSE,
                which,
            )
            assert_record_ids(
                record,
                self.id_fields,
                {
                    "caller_id": str(CALLER_ID),
                    "document_id": str(self.first_document_id),
                    self.child_id_field: ABSENT,
                },
                which,
            )
            self._assert_whole_extra_set(record, EXTRA_FIELDS_AT_STEP_TWO, which)

    def assert_every_unresolvable_probe_was_the_canonical_refusal(self) -> None:
        """The caller-facing half, pinned as the whole body rather than the type.

        `captured` only ever checked the exception's class, so a guard that
        recorded the right step-1 record while leaking the probed number -- or the
        id of a document the caller has no claim to -- into the 404 text passed
        everything here. This is the path where such a disclosure would appear.
        """
        for case in UNRESOLVABLE_CASES:
            outcome, _ = self._unresolvable[case]
            assert_is_the_canonical_refusal(outcome, self._describe(case))

    def assert_an_unresolvable_document_still_records_the_attribution(self) -> None:
        """The load-bearing one: the parse must not run ahead of the document guard.

        Both orderings answer the caller the identical canonical 404 and leave the
        revision store untouched, so nothing else in this suite tells them apart.
        If the parse ran first, an unusable number would short-circuit before step
        1 ever looked the document up, and a caller enumerating document ids could
        switch the attribution channel off for themselves with `/0/restore` or
        `/abc/restore` -- exactly the ids the step-1 cause exists to record.
        """
        for case in UNRESOLVABLE_CASES:
            which = self._describe(case)
            record = self._first(self._unresolvable[case][1], which)
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
        enumerated -- the probed number under some new name, an ip, an owner id --
        is invisible to it. The whole-set rule is reused from
        `refusal_record_shape_statements` rather than restated.
        """
        actual = extra_field_names(record)
        assert actual == expected, (
            f"the {which} refusal record attached the extras {sorted(actual)}, expected "
            f"{sorted(expected)} -- a field outside the enumerated roster passes every "
            f"id check while carrying something the caller proved no claim to"
        )

    def _describe(self, case: tuple[str, str]) -> str:
        path, probe = case
        return f"revision number '{probe}' under {path}"
