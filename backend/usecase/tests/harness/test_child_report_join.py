from statements.bannerless_child_report_statements import BannerlessChildReportStatements
from statements.child_report_join_statements import ChildReportJoinStatements


class TestChildReportJoin:
    """A child's two output streams must not be able to eat each other's lines.

    `ChildPytestReport` fuses the streams with `+`, and every assertion the
    forgotten-await gate makes is positional over that fused text: the tally is the
    last banner, and a section is the span between two banners. A merged final line
    stops being a banner, so the tally reads `{}` and the section runs to the end of
    the report -- and the gate reports both as pytest misbehaving.
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


class TestBannerlessChildReport:
    """A child that died before its first banner tallies empty, and says why.

    `summary_counts()` reads `banners[-1]`; with no banner there is nothing to
    read. That empty tally is the exact symptom the stream join was fixed to stop
    producing spuriously -- and the arm that produces it legitimately has never
    been executed, so nothing has ever proved it answers `{}` rather than raising
    `IndexError` at the gate.
    """

    def test_should_tally_nothing_when_the_child_drew_no_banner_at_all(
        self, bannerless_child_report_statements: BannerlessChildReportStatements
    ):
        """Given a child that was refused its arguments and printed only a usage error
        When its report is read for a tally
        Then the tally is empty, and the report is exactly that child's two streams
        """
        bannerless_child_report_statements.given_a_child_that_drew_no_banner_at_all()

        bannerless_child_report_statements.assert_the_bannerless_report_tallies_nothing()

    def test_should_still_tally_the_banner_when_the_same_diagnostic_follows_a_report(
        self, bannerless_child_report_statements: BannerlessChildReportStatements
    ):
        """The control: the emptiness above must come from the absent banner.

        Given a child that printed a full report and the same usage diagnostic on stderr
        When its report is read for a tally
        Then the tally is the one stdout reported, off a report proven to carry that stderr

        Without this, the empty tally beside it is equally explained by the stderr
        text, by the join dropping stdout, or by `summary_counts()` answering `{}`
        for every input.
        """
        bannerless_child_report_statements.given_a_child_whose_diagnostic_followed_a_real_report()

        bannerless_child_report_statements.assert_the_same_diagnostic_still_tallies_a_real_banner()
