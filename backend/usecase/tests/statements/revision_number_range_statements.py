from statements.document_guard_contract import assert_is_the_canonical_refusal, outcome_of
from statements.revision_guard_base import RevisionGuardBase

# The storage range, written as the two literals the `INTEGER` column actually
# holds. Not read back from production, and not computed as `2**31 - 1`: the claim
# under test is that somebody wrote *this* bound down, and a test that recomputes
# it agrees with any arithmetic the guard performs, including the wrong one.
SMALLEST_VALID_REVISION_NUMBER = "1"
LARGEST_VALID_REVISION_NUMBER = "2147483647"

# Python ints are unbounded and the column is not. Passing any of these through
# reaches the driver as a numeric-out-of-range error, which the guard's
# deliberately narrow `except NotFoundException` correctly does not swallow -- so
# it would surface as a 500, which `documents_revisions_restore.yaml` forbids
# ("overflowing → 404").
OUT_OF_RANGE_REVISION_NUMBERS = ("0", "-1", "-2147483648", "2147483648")

# Values `int()` refuses outright. Deliberately unambiguous: `" 2"`, `"+2"`, `"1_0"`
# and the Arabic-Indic `"٢"` are all *accepted* by `int()`, so demanding a refusal
# for them would pin a parser opinion this scenario has not formed. What is here
# instead are the numeric-looking strings a hand-rolled check would let past --
# `"1.5"`, `"2e3"` and `"0x2"` all survive a `float()` or a lenient regex.
NON_INTEGER_REVISION_NUMBERS = ("abc", "1.5", "", "2e3", "0x2", "-")


class RevisionNumberRangeStatements(RevisionGuardBase):
    """Parsing and range-checking happen before the store is asked anything.

    Both edges answer the canonical 404 rather than a 422 or a 500, and both are
    counted rather than merely observed: the refusal alone is satisfied by a guard
    that hands the value to the repository and lets the miss answer for it, which
    is precisely the shape that becomes a 500 the day a real int4 column is behind
    the port.
    """

    def __init__(self) -> None:
        super().__init__()
        self._refusals: dict[str, object] = {}
        self._boundary_outcomes: dict[str, object] = {}

    async def request_every_out_of_range_revision_number(self) -> None:
        await self._request_each(OUT_OF_RANGE_REVISION_NUMBERS)

    async def request_every_non_integer_revision_number(self) -> None:
        await self._request_each(NON_INTEGER_REVISION_NUMBERS)

    async def request_both_ends_of_the_valid_range(self) -> None:
        """The positive control against a range check that refuses everything.

        Neither number is seeded, so both are ordinary 404s. Recorded and not
        judged, for the reason `_request_each` gives.
        """
        for value in (SMALLEST_VALID_REVISION_NUMBER, LARGEST_VALID_REVISION_NUMBER):
            self._boundary_outcomes[value] = await outcome_of(
                self.resolve(self.first_document_id, value)
            )

    async def _request_each(self, values: tuple[str, ...]) -> None:
        """Records what each probe came back with; judges none of it.

        `outcome_of` rather than `refusal_of`: the latter runs through `captured`,
        which enforces the exception type and fails when the guard returns instead
        of refusing -- a real contract applied from inside the act half, where no
        reader of the test body can see it. Nothing is lost by moving it out:
        `_assert_each_refusal_was_canonical` pins type and body together, and it
        takes `object` precisely so "the guard returned a scope" fails there.
        """
        for value in values:
            self._refusals[value] = await outcome_of(self.resolve(self.first_document_id, value))

    def assert_every_out_of_range_refusal_was_canonical(self) -> None:
        self._assert_each_refusal_was_canonical(OUT_OF_RANGE_REVISION_NUMBERS, "out-of-range")

    def assert_every_non_integer_refusal_was_canonical(self) -> None:
        self._assert_each_refusal_was_canonical(NON_INTEGER_REVISION_NUMBERS, "non-integer")

    def _assert_each_refusal_was_canonical(self, expected: tuple[str, ...], which: str) -> None:
        """The roster is pinned before it is walked.

        Looping over whatever the act step happened to record makes the loop agree
        with any subset of it, including the empty one: a request step that probed
        one of four values, or none, would satisfy a bare `for` over its own
        results. The literal tuple is the same one the act step was handed, so what
        this pins is that every value in it actually reached the guard.
        """
        assert tuple(self._refusals) == expected, (
            f"the {which} probe covered {tuple(self._refusals)}, expected every one of "
            f"{expected} -- a roster read back off the act step agrees with any subset of "
            f"itself, so the values that were never sent would go unnoticed"
        )
        # Indexed out of the pinned tuple rather than walked as `self._refusals.items()`:
        # iterating what the act step happened to record makes the loop body agree with
        # any subset of it, and it leaves the roster equality above as the only thing
        # standing between a skipped probe and a green run. Indexing fails on the value
        # that was never sent even if that equality is ever relaxed.
        for value in expected:
            assert_is_the_canonical_refusal(self._refusals[value], f"revision number '{value}'")

    def assert_the_store_was_never_asked(self) -> None:
        self._assert_revision_lookups(
            [],
            f"each of {sorted(self._refusals)} must be refused by the guard itself; handing any "
            f"of them to the repository sends the driver a value its int4 column cannot hold, "
            f"and the narrow `except NotFoundException` turns that into the 500 the restore "
            f"contract forbids",
        )

    def assert_both_ends_were_ordinary_misses(self) -> None:
        """In-range and unseeded is a 404 from the store, not from the range check.

        Same canonical body as an out-of-range refusal -- which is the point: the
        two are indistinguishable to the caller, and only the call log below tells
        them apart.
        """
        expected = (SMALLEST_VALID_REVISION_NUMBER, LARGEST_VALID_REVISION_NUMBER)
        assert tuple(self._boundary_outcomes) == expected, (
            f"the boundary probe covered {tuple(self._boundary_outcomes)}, expected {expected}"
        )
        for value in expected:
            assert_is_the_canonical_refusal(
                self._boundary_outcomes[value], f"in-range revision number '{value}'"
            )

    def assert_both_ends_of_the_valid_range_reached_the_store(self) -> None:
        """Expected written as the two ints, not recomputed from the act step.

        Deriving the expectation by `int()`-ing the values the act step recorded
        makes it agree with whatever ran -- including nothing at all, where an
        empty expectation matches an untouched store and the positive control
        silently stops being one.
        """
        self._assert_revision_lookups(
            [(1, self.first_document_id), (2147483647, self.first_document_id)],
            "1 and 2147483647 are inside the storage range, so the guard must parse them to "
            "ints and ask -- a check that refuses its own boundaries would satisfy every other "
            "assertion in this class",
        )
