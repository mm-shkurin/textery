"""The seam where a child run's two output streams are joined into one text.

`ChildPytestReport` fuses stdout and stderr with `+` and no separator, and every
assertion the forgotten-await gate makes is read off that fused text: the session
header lines by `startswith`, the report sections by banner position, and the
tally by `banners[-1]`. Two consequences, both silent:

* stderr lands *after* the final tally banner, so anything the child writes there
  -- a warning from the interpreter, a plugin's diagnostics -- can carry a banner
  of its own and become the last one `summary_counts()` reads.
* stdout without a trailing newline merges its last line with stderr's first, so
  the final tally banner stops matching the banner pattern at all and the tally
  reads `{}` -- which the gate reports as "the child summarised {}, expected
  {'failed': 1}", pointing the reader at pytest rather than at the join.

The fabrication and the assertions are shared with the bannerless family; see
`fabricated_child_report_statements`.
"""

from statements.fabricated_child_report_statements import (
    REPORTED_FAILURES_EXIT_CODE,
    STDOUT_WITHOUT_A_TRAILING_NEWLINE,
    TALLY_STDOUT_REPORTED,
    FabricatedChildReportStatements,
)

# What a child writes to the other stream. Innocuous prose, and it carries no
# banner of its own -- the failure under test is the *merge*, not a competing
# tally, so the fabricated stderr must not be able to be blamed for one.
STDERR_NOISE = "Exception ignored in: <coroutine object>\n"

# Exactly what the two streams must read as once joined -- `"\n".join` of them,
# pinned whole so the tally below is read off a report proven to carry both.
REPORT_OF_BOTH_STREAMS = STDOUT_WITHOUT_A_TRAILING_NEWLINE + "\n" + STDERR_NOISE


class ChildReportJoinStatements(FabricatedChildReportStatements):
    """Read a fabricated two-stream child report, and pin what the join loses."""

    def given_a_child_that_wrote_to_both_streams(self) -> None:
        self._fabricate(
            stdout=STDOUT_WITHOUT_A_TRAILING_NEWLINE,
            stderr=STDERR_NOISE,
            returncode=REPORTED_FAILURES_EXIT_CODE,
        )

    def assert_the_tally_survived_the_second_stream(self) -> None:
        self._assert_the_report_is(
            REPORT_OF_BOTH_STREAMS,
            "a tally read off a report that lost one of the two streams says nothing about "
            "the join",
        )
        self._assert_the_tally_is(
            TALLY_STDOUT_REPORTED,
            "stdout and stderr are joined with `+`, so a missing trailing newline merges "
            "the final tally banner into the first stderr line and every tally assertion "
            "in the gate reads `{}` while blaming pytest",
        )

    def assert_the_failures_section_survived_the_second_stream(self) -> None:
        """The other half of the same join, and the one that reads as a real defect.

        `section()` slices between banner *line numbers*; a merged final banner
        moves the end of the FAILURES section, so the section the gate searches for
        the unawaited-coroutine sentence silently swallows the tally line and
        whatever stderr wrote after it.
        """
        self._assert_the_report_is(
            REPORT_OF_BOTH_STREAMS,
            "a section read off a report that lost one of the two streams says nothing "
            "about the join",
        )
        self._assert_the_failures_section_is_the_one_stdout_reported(
            "the section is bounded by the next banner, and a banner merged away by the "
            "stream join moves that bound past the end of the report"
        )
