"""A finished child run, built rather than run, and the ways it is read back.

Two scenario families address a fabricated `CompletedProcess`: the stream *join*
(`child_report_join_statements`) and the *bannerless* report that reaches
`summary_counts()`' empty-banners arm (`bannerless_child_report_statements`).
They share the fabrication and the four things worth asserting about the result,
and nothing else -- so the shared half lives here and each family states only its
own arrangement and its own claims.

Fabricated rather than run: the subject is the reading, not the running, and
neither a stdout without a trailing newline nor a child that dies before its
first banner is something a real run can be asked for on demand.
"""

import subprocess

from statements.arranged import arranged
from statements.child_pytest_report import FAILURES_SECTION, ChildPytestReport

# The one test the fabricated report is about. Named because the stdout constant
# below spells it inside a banner and the expected FAILURES body spells it again
# -- two hand-synchronised literals, and the drift would read as a `section()` bug.
FAILING_TEST_NAME = "test_probe"

# A complete pytest report, deliberately without the trailing newline a terminal
# run happens to end with -- the join must not depend on the child's last byte.
STDOUT_WITHOUT_A_TRAILING_NEWLINE = (
    "============================= test session starts =============================\n"
    "rootdir: /somewhere\n"
    "collected 1 item\n"
    "\n"
    f"{FAILING_TEST_NAME}.py F\n"
    "\n"
    "=================================== FAILURES ==================================\n"
    f"{FAILING_TEST_NAME}\n"
    "\n"
    "============================== 1 failed in 0.42s =============================="
)

# What that stdout's final banner and FAILURES section say, as values. Both are
# properties of the constant above; naming them keeps the expectation and the
# fixture from drifting apart in opposite directions.
TALLY_STDOUT_REPORTED = {"failed": 1}
FAILURES_BODY_STDOUT_REPORTED = f"{FAILING_TEST_NAME}\n"

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
# What a run that got as far as reporting a failure exits with.
REPORTED_FAILURES_EXIT_CODE = 1


class FabricatedChildReportStatements:
    """Holds one fabricated report, and states the four claims worth making of it.

    Every assertion is whole-value. `output` in particular is pinned by equality
    rather than searched for a sentence: every byte of these fixtures is written
    by this package, so containment would buy nothing and would still pass on a
    report carrying extra lines the join invented.
    """

    def __init__(self) -> None:
        self._report: ChildPytestReport | None = None

    def _fabricate(self, stdout: str, stderr: str, returncode: int) -> None:
        self._report = ChildPytestReport(
            subprocess.CompletedProcess(
                args=["pytest"], returncode=returncode, stdout=stdout, stderr=stderr
            )
        )

    def _assert_the_report_is(self, expected: str, because: str) -> None:
        actual = self._child().output
        assert actual == expected, (
            f"the joined report read '{actual}', expected '{expected}' -- {because}"
        )

    def _assert_the_exit_code_is(self, expected: int, because: str) -> None:
        actual = self._child().exit_code
        assert actual == expected, (
            f"the report exited {actual}, expected {expected} -- {because}"
        )

    def _assert_the_tally_is(self, expected: dict[str, int], because: str) -> None:
        actual = self._child().summary_counts()
        assert actual == expected, (
            f"the report summarised {actual}, expected {expected} -- {because}"
        )

    def _assert_the_failures_section_is(self, because: str) -> None:
        actual = self._child().section(FAILURES_SECTION)
        assert actual == FAILURES_BODY_STDOUT_REPORTED, (
            f"the FAILURES section read '{actual}', expected "
            f"'{FAILURES_BODY_STDOUT_REPORTED}' -- {because}"
        )

    def _child(self) -> ChildPytestReport:
        return arranged(self._report, "the fabricated child report")
