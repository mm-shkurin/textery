import pytest

from statements.child_report_join_statements import ChildReportJoinStatements


class TestChildReportJoin:
    """A child's two output streams must not be able to eat each other's lines.

    Given a child run whose stdout has no trailing newline and whose stderr is not empty
    When its report is read for a tally and for the FAILURES section
    Then both are the ones stdout actually reported

    `ChildPytestReport` fuses the streams with `+`, and every assertion the
    forgotten-await gate makes is positional over that fused text: the tally is the
    last banner, and a section is the span between two banners. A merged final line
    stops being a banner, so the tally reads `{}` and the section runs to the end of
    the report -- and the gate reports both as pytest misbehaving.
    """

    @pytest.mark.skip(reason="RED: separating the two streams in ChildPytestReport is GREEN's")
    def test_should_read_the_tally_when_the_child_also_wrote_to_stderr(
        self, child_report_join_statements: ChildReportJoinStatements
    ):
        child_report_join_statements.given_a_child_that_wrote_to_both_streams()

        child_report_join_statements.assert_the_tally_survived_the_second_stream()

    @pytest.mark.skip(reason="RED: separating the two streams in ChildPytestReport is GREEN's")
    def test_should_bound_the_failures_section_when_the_child_also_wrote_to_stderr(
        self, child_report_join_statements: ChildReportJoinStatements
    ):
        child_report_join_statements.given_a_child_that_wrote_to_both_streams()

        child_report_join_statements.assert_the_failures_section_survived_the_second_stream()
