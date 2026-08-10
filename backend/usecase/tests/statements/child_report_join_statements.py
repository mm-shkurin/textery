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

Driven from a fabricated `CompletedProcess` rather than a real child run: the
subject is the reading, not the running, and a real child that reliably writes to
stderr without a trailing stdout newline is not something a test can arrange.
"""

import subprocess

from statements.arranged import arranged
from statements.child_pytest_report import ChildPytestReport

# A complete pytest report, deliberately without the trailing newline a terminal
# run happens to end with -- the join must not depend on the child's last byte.
STDOUT_WITHOUT_A_TRAILING_NEWLINE = (
    "============================= test session starts =============================\n"
    "rootdir: /somewhere\n"
    "collected 1 item\n"
    "\n"
    "test_probe.py F\n"
    "\n"
    "=================================== FAILURES ==================================\n"
    "test_probe\n"
    "\n"
    "============================== 1 failed in 0.42s =============================="
)

# What a child writes to the other stream. Innocuous prose, and it carries no
# banner of its own -- the failure under test is the *merge*, not a competing
# tally, so the fabricated stderr must not be able to be blamed for one.
STDERR_NOISE = "Exception ignored in: <coroutine object>\n"


class ChildReportJoinStatements:
    """Read a fabricated two-stream child report, and pin what the join loses."""

    def __init__(self) -> None:
        self._report: ChildPytestReport | None = None

    def given_a_child_that_wrote_to_both_streams(self) -> None:
        self._report = ChildPytestReport(
            subprocess.CompletedProcess(
                args=["pytest"],
                returncode=1,
                stdout=STDOUT_WITHOUT_A_TRAILING_NEWLINE,
                stderr=STDERR_NOISE,
            )
        )

    def assert_the_tally_survived_the_second_stream(self) -> None:
        actual = self._child().summary_counts()
        expected = {"failed": 1}
        assert actual == expected, (
            f"the report summarised {actual}, expected {expected} -- stdout and stderr are "
            f"joined with `+`, so a missing trailing newline merges the final tally banner "
            f"into the first stderr line and every tally assertion in the gate reads `{{}}` "
            f"while blaming pytest"
        )

    def assert_the_failures_section_survived_the_second_stream(self) -> None:
        """The other half of the same join, and the one that reads as a real defect.

        `section()` slices between banner *line numbers*; a merged final banner
        moves the end of the FAILURES section, so the section the gate searches for
        the unawaited-coroutine sentence silently swallows the tally line and
        whatever stderr wrote after it.
        """
        actual = self._child().section("FAILURES")
        expected = "test_probe\n"
        assert actual == expected, (
            f"the FAILURES section read '{actual}', expected '{expected}' -- the section is "
            f"bounded by the next banner, and a banner merged away by the stream join moves "
            f"that bound past the end of the report"
        )

    def _child(self) -> ChildPytestReport:
        return arranged(self._report, "the fabricated child report")
