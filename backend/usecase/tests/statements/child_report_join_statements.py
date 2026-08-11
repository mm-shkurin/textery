"""The seam where a child run's two output streams are joined into one text.

`ChildPytestReport` joins stdout and stderr with `"\\n".join`, and every assertion
the forgotten-await gate makes is read off that joined text: the session header
lines by `startswith`, the report sections by banner position, and the tally by
`banners[-1]`. The separator is what these tests hold in place. It was once a bare
`+`, and the consequence was silent: stdout without a trailing newline merged its
last line with stderr's first, the final tally banner stopped matching the banner
pattern at all, and the tally read `{}` -- which the gate reported as "the child
summarised {}, expected {'failed': 1}", pointing the reader at pytest rather than
at the join. That defect is fixed; these tests exist so a future `+` cannot
reintroduce it unnoticed.

The separator fixed the *merge*; it did nothing about the *order*. stderr still
lands after the final tally banner, so anything the child writes there carrying a
`=+ ... =+` line of its own becomes the last banner `summary_counts()` reads --
which is the same "the gate blames pytest for it" failure by the other door, and
the one the original fixture was deliberately built to be unable to see. Both are
now stated: `STDERR_NOISE` carries no banner and holds the separator, and
`STDERR_CARRYING_ITS_OWN_BANNER` carries one and holds the ordering.

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

# A stderr line shaped exactly like pytest's closing tally banner. Not contrived:
# a child that itself shells out to pytest, a wrapper script echoing a summary, or
# a plugin writing its own separator all produce one, and `_BANNER` is matched
# against the joined text with no idea which stream a line came from.
#
# A *different* tally from stdout's, and deliberately not a superset of it: read by
# accident, `{'failed': 3}` cannot agree with the right answer for the wrong
# reason, which `1 failed` on both streams would.
STDERR_CARRYING_ITS_OWN_BANNER = (
    "============================== 3 failed in 9.99s ==============================\n"
)

REPORT_OF_A_BANNER_CARRYING_STDERR = (
    STDOUT_WITHOUT_A_TRAILING_NEWLINE + "\n" + STDERR_CARRYING_ITS_OWN_BANNER
)


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
            "joined with a bare `+` instead of a newline, a stdout missing its trailing "
            "newline merges the final tally banner into the first stderr line and every "
            "tally assertion in the gate reads `{}` while blaming pytest",
        )

    def assert_the_failures_section_survived_the_second_stream(self) -> None:
        """The other half of the same join, and the one that reads as a real defect.

        `section()` slices between banner *line numbers*; a final banner merged away
        by a `+` join moves the end of the FAILURES section, so the section the gate
        searches for the unawaited-coroutine sentence silently swallows the tally
        line and whatever stderr wrote after it.
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

    def given_a_child_whose_stderr_carries_a_banner_of_its_own(self) -> None:
        self._fabricate(
            stdout=STDOUT_WITHOUT_A_TRAILING_NEWLINE,
            stderr=STDERR_CARRYING_ITS_OWN_BANNER,
            returncode=REPORTED_FAILURES_EXIT_CODE,
        )

    def assert_the_tally_was_read_off_the_stdout_banner(self) -> None:
        """The half the separator never addressed: stderr lands *after* the tally.

        `summary_counts()` takes `banners[-1]`, and the join appends stderr to the
        end of the report -- so a stderr line shaped like a banner is the last one,
        and the tally the gate reports is stderr's rather than pytest's. That is
        the same reader-facing failure the `+` join produced ("the child summarised
        X, expected Y", pointing at pytest), reached by ordering rather than by
        merging, and the original fixture could not see it because its stderr was
        chosen to carry no banner.

        The section is asserted in the same breath because it is the half that is
        *already* right and must stay so: a repair that discarded stderr, or that
        stopped at the first banner instead of the last, would fix the tally and
        move the section's bound. Pinning the report whole first is what keeps
        either claim from being satisfied by a reading that lost a stream.
        """
        self._assert_the_report_is(
            REPORT_OF_A_BANNER_CARRYING_STDERR,
            "a tally read off a report that lost one of the two streams says nothing about "
            "which stream the tally came from",
        )
        self._assert_the_tally_is(
            TALLY_STDOUT_REPORTED,
            "the tally is `banners[-1]` and stderr is joined after stdout, so a child whose "
            "stderr carries a banner of its own has that banner read as pytest's closing "
            "tally -- and the gate then reports a count no pytest ever wrote",
        )
        self._assert_the_failures_section_is_the_one_stdout_reported(
            "a section is the span to the next banner, so a banner arriving from stderr "
            "must not be allowed to move where stdout's sections end"
        )
