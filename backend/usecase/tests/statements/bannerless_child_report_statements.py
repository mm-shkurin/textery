"""A child that died before pytest drew its first banner, and the tally that gives.

`summary_counts()` reads the tally off `banners[-1]`, so a report with no banner
has nothing to read and answers `{}` instead of raising `IndexError`. That arm
has never been executed -- and the `{}` it returns is the exact symptom the
stream join was fixed to stop the gate from producing spuriously, so the arm that
produces it *legitimately* is worth pinning on its own.

An `== {}` asserted alone is satisfied by every way a report can be bannerless
for the wrong reason: a fixture that never ran, an empty `CompletedProcess`, a
`_lines` that lost the streams, or a report whose banners are present but tally
to nothing. So the joined report is pinned whole first -- which is itself the
proof of bannerlessness, since there is no `=+ ... =+` line anywhere in it -- and
the exit code with it. The control beside it holds the identical stderr behind a
stdout that *does* carry a final tally banner.
"""

from statements.fabricated_child_report_statements import (
    REPORTED_FAILURES_EXIT_CODE,
    STDOUT_WITHOUT_A_TRAILING_NEWLINE,
    TALLY_STDOUT_REPORTED,
    FabricatedChildReportStatements,
)

# A child that died before pytest drew its first banner: an argument it did not
# recognise, refused during `_preparse`. Substantive output, four lines of it,
# and not one `=+ ... =+` line anywhere -- which is the only shape that reaches
# `summary_counts()`' empty-banners arm.
STDERR_OF_A_CHILD_THAT_NEVER_STARTED = (
    "ERROR: usage: __main__.py [options] [file_or_dir] [file_or_dir] [...]\n"
    "__main__.py: error: unrecognized arguments: --not-an-option\n"
    "  inifile: /somewhere/pyproject.toml\n"
    "  rootdir: /somewhere\n"
)

# pytest's exit code for a usage error -- neither the 0 of a clean run nor the 1
# of a run that reported failures, so the tally being empty is the only thing
# left that could say what happened.
USAGE_ERROR_EXIT_CODE = 4

# Exactly what each fabrication reads as once joined -- `"\n".join` of the two
# streams. Pinned by equality rather than searched for the child's diagnostic
# sentence: every byte is written here, so containment would buy nothing and
# would still pass on a report carrying extra lines the join invented.
REPORT_OF_A_CHILD_THAT_NEVER_STARTED = "\n" + STDERR_OF_A_CHILD_THAT_NEVER_STARTED
REPORT_WITH_THE_DIAGNOSTIC_BEHIND_A_BANNER = (
    STDOUT_WITHOUT_A_TRAILING_NEWLINE + "\n" + STDERR_OF_A_CHILD_THAT_NEVER_STARTED
)


class BannerlessChildReportStatements(FabricatedChildReportStatements):
    """Pin the empty-banners arm, and the control that stops it being vacuous."""

    def given_a_child_that_drew_no_banner_at_all(self) -> None:
        self._fabricate(
            stdout="",
            stderr=STDERR_OF_A_CHILD_THAT_NEVER_STARTED,
            returncode=USAGE_ERROR_EXIT_CODE,
        )

    def given_a_child_whose_diagnostic_followed_a_real_report(self) -> None:
        """The control: the same stderr, behind a report that *does* carry a tally."""
        self._fabricate(
            stdout=STDOUT_WITHOUT_A_TRAILING_NEWLINE,
            stderr=STDERR_OF_A_CHILD_THAT_NEVER_STARTED,
            returncode=REPORTED_FAILURES_EXIT_CODE,
        )

    def assert_the_bannerless_report_tallies_nothing(self) -> None:
        """The empty-banners arm, with its premise asserted rather than assumed."""
        self._assert_the_report_is(
            REPORT_OF_A_CHILD_THAT_NEVER_STARTED,
            "a report that is not exactly the crashed child's two streams is not this "
            "subject at all -- and one carrying a banner line would reach the tally "
            "through a different arm entirely",
        )
        self._assert_the_exit_code_is(
            USAGE_ERROR_EXIT_CODE,
            "a bannerless report from a run that exited 0 or 1 would be a different subject",
        )
        self._assert_the_tally_is(
            {},
            "there is no banner in it to read a tally off, and inventing one would let the "
            "gate report a tally the child never printed",
        )

    def assert_the_same_diagnostic_still_tallies_a_real_banner(self) -> None:
        """The control that makes the assertion above non-vacuous.

        The identical stderr, behind a stdout that does carry a final tally
        banner, must tally that banner and bound its FAILURES section where the
        banner sits. Without this, `{}` above is equally explained by the
        diagnostic text suppressing the tally, by the join dropping stdout, or by
        `summary_counts()` being broken for every input -- and a guard that passes
        in the state it exists to reject is the shape this scenario has already
        shipped five times.
        """
        self._assert_the_report_is(
            REPORT_WITH_THE_DIAGNOSTIC_BEHIND_A_BANNER,
            "the control only isolates the absence of banners if the very same stderr "
            "demonstrably reached this report too",
        )
        self._assert_the_exit_code_is(
            REPORTED_FAILURES_EXIT_CODE,
            "the control is a run that got as far as reporting a failure, not one refused "
            "its arguments",
        )
        self._assert_the_failures_section_is_the_one_stdout_reported(
            "four extra stderr lines behind the final banner must stay outside the section"
        )
        self._assert_the_tally_is(
            TALLY_STDOUT_REPORTED,
            "the same stderr behind a real tally banner must still tally it, or the empty "
            "tally beside it says nothing about the absence of banners",
        )
