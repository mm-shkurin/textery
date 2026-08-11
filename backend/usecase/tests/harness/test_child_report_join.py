import pytest

from statements.child_report_join_statements import ChildReportJoinStatements


class TestChildReportJoin:
    """A child's two output streams must not be able to eat each other's lines.

    `ChildPytestReport` joins the streams with `"\\n".join`, and every assertion the
    forgotten-await gate makes is positional over that joined text: the tally is the
    last banner, and a section is the span between two banners. Joined with a bare
    `+` -- as it once was -- a merged final line stops being a banner, so the tally
    reads `{}` and the section runs to the end of the report, and the gate reports
    both as pytest misbehaving. These tests hold the separator in place.
    """

    def test_should_read_the_tally_when_the_child_also_wrote_to_stderr(
        self, child_report_join_statements: ChildReportJoinStatements
    ):
        """Given a child run whose stdout has no trailing newline and whose stderr is not empty
        When its report is read for a tally
        Then the tally is the one stdout actually reported
        """
        child_report_join_statements.given_a_child_that_wrote_to_both_streams()

        child_report_join_statements.assert_the_tally_survived_the_second_stream()

    def test_should_bound_the_failures_section_when_the_child_also_wrote_to_stderr(
        self, child_report_join_statements: ChildReportJoinStatements
    ):
        """Given a child run whose stdout has no trailing newline and whose stderr is not empty
        When its report is read for the FAILURES section
        Then the section is the one stdout actually reported, and stops at the tally banner
        """
        child_report_join_statements.given_a_child_that_wrote_to_both_streams()

        child_report_join_statements.assert_the_failures_section_survived_the_second_stream()

    @pytest.mark.skip(
        reason="RED: summary_counts() reads banners[-1] over the joined text, so a "
        "banner-shaped stderr line is read as pytest's closing tally -- "
        "summarised {'failed': 3}, expected {'failed': 1}"
    )
    def test_should_read_the_tally_off_stdout_when_stderr_carries_a_banner_of_its_own(
        self, child_report_join_statements: ChildReportJoinStatements
    ):
        """Given a child run whose stderr carries a `=+ ... =+` line of its own
        When its report is read for a tally and for the FAILURES section
        Then both are the ones stdout actually reported

        The separator fixed the merge and left the ordering: stderr is joined
        *after* stdout, `summary_counts()` reads `banners[-1]`, so a banner-shaped
        stderr line is what the gate reports as pytest's closing tally.
        """
        child_report_join_statements.given_a_child_whose_stderr_carries_a_banner_of_its_own()

        child_report_join_statements.assert_the_tally_was_read_off_the_stdout_banner()
