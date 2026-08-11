"""A child whose banners arrived wrapped in ANSI colour, and what the reader makes of them.

pytest's terminal writer turns markup on in a non-tty whenever `PY_COLORS=1` or
`FORCE_COLOR` is set -- `should_do_markup` checks exactly those two -- and
`write_sep` then wraps the *whole* separator line, so every banner the child draws
begins with `\\x1b[` and ends with `\\x1b[0m`.

`_BANNER = re.compile(r"^=+ (?P<name>.+?) =+$")` is anchored, so it matches none of
them: `_banners()` answers `[]`, `summary_counts()` takes its empty-banners arm,
and the gate reports `the child summarised {}, expected {'failed': 1}` -- a
sentence that points the reader at pytest for a report pytest wrote correctly.
`LEAKY_CHILD_VARIABLES` scrubs five names and not one of them is a colour
variable, so a runner exporting `PY_COLORS=1` puts every gate in this package into
that state at once.

The bannerless family beside this one sanctioned `{}` as the honest answer for a
report with no banner in it. This family is what keeps that sanction narrow: a
report that *is* full of banners must never reach the same answer.
"""

from statements.fabricated_child_report_statements import (
    FAILING_TEST_NAME,
    REPORTED_FAILURES_EXIT_CODE,
    TALLY_STDOUT_REPORTED,
    FabricatedChildReportStatements,
)

# What `write_sep` puts around a separator line once markup is on: pytest's
# `green` for a passing-looking run, and the reset it always closes with.
_MARKUP_ON = "\x1b[32m"
_MARKUP_OFF = "\x1b[0m"

# The same report the plain fixture spells, with markup around each separator
# line and nothing else -- typed out rather than derived from that fixture by a
# regex that re-decorates it. Derivation made the premise assertion below
# vacuous: expected and actual came out of the same helper, so a separator
# pattern that stopped matching would have left *both* uncoloured and the claim
# "the escapes are in the text the reader is handed" would still have passed --
# in exactly the state it exists to reject. Spelled as bytes, the escapes are
# pinned by the equality itself.
COLOURED_STDOUT = (
    f"{_MARKUP_ON}"
    "============================= test session starts ============================="
    f"{_MARKUP_OFF}\n"
    "rootdir: /somewhere\n"
    "collected 1 item\n"
    "\n"
    f"{FAILING_TEST_NAME}.py F\n"
    "\n"
    f"{_MARKUP_ON}"
    "=================================== FAILURES =================================="
    f"{_MARKUP_OFF}\n"
    f"{FAILING_TEST_NAME}\n"
    "\n"
    f"{_MARKUP_ON}"
    "============================== 1 failed in 0.42s =============================="
    f"{_MARKUP_OFF}"
)

# The two streams as the reader receives them -- `"\n".join` of a coloured stdout
# and an empty stderr. Pinned whole so the claims below are read off a report
# proven to still *carry* the escapes: a subject that answers the right tally by
# deleting the child's own bytes from `output` has not read through the colour,
# it has rewritten the evidence, and `tail` would then diagnose a report nobody ran.
COLOURED_REPORT = COLOURED_STDOUT + "\n"


class ColouredChildReportStatements(FabricatedChildReportStatements):
    """Read a report whose banners are colour-wrapped, and require them to be seen."""

    def given_a_child_that_coloured_every_banner(self) -> None:
        self._fabricate(
            stdout=COLOURED_STDOUT,
            stderr="",
            returncode=REPORTED_FAILURES_EXIT_CODE,
        )

    def assert_the_coloured_report_is_read_through_its_markup(self) -> None:
        """The tally and the section, off a report whose every banner is escaped."""
        self._assert_the_report_is(
            COLOURED_REPORT,
            "the escapes have to be in the text the reader is handed, or the claim below "
            "is made about an uncoloured report and guards nothing",
        )
        self._assert_the_tally_is(
            TALLY_STDOUT_REPORTED,
            "a runner exporting PY_COLORS=1 wraps every banner in ANSI, the anchored "
            "banner pattern then matches none of them, and this report -- which reported "
            "a failure -- tallies as the empty dict the bannerless arm exists for",
        )
        self._assert_the_failures_section_is_the_one_stdout_reported(
            "sections are bounded by banner line numbers too, so a fix applied only where "
            "the tally is parsed leaves the gate searching an unbounded FAILURES section "
            "for the sentence it was written to find"
        )
