from statements.coloured_child_report_statements import ColouredChildReportStatements


class TestColouredChildReport:
    """A colour-decorated report is not a bannerless one, and must not tally as one.

    pytest enables markup in a non-tty on `PY_COLORS=1` or `FORCE_COLOR`, and then
    wraps every `==== ... ====` separator in ANSI escapes. The anchored banner
    pattern matches none of them, so a child that reported a failure summarises to
    the empty dict -- the same answer the bannerless family established as correct
    for a child that drew no banner at all. Nothing else in this package tells the
    two apart, and the gate blames pytest for both.
    """

    def test_should_tally_the_report_when_the_child_coloured_every_banner(
        self, coloured_child_report_statements: ColouredChildReportStatements
    ):
        """Given a child whose every banner line arrived wrapped in ANSI colour
        When its report is read for a tally and for the FAILURES section
        Then both are the ones stdout reported, off a report still carrying the escapes
        """
        coloured_child_report_statements.given_a_child_that_coloured_every_banner()

        coloured_child_report_statements.assert_the_coloured_report_is_read_through_its_markup()
