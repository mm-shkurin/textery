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
