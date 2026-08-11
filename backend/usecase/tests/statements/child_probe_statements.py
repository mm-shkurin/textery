"""What every family that proves a claim about the harness has in common.

More than one guard in this suite makes a claim that cannot be driven red from
inside the suite -- the forgotten-await gate, the gate's own reach, the live
arming check. All of them take the same shape: write a probe module, run it as a
child pytest under this project's own `pyproject.toml`, and read the child's
report. What differs between them is only the probe and what the child is
expected to say.

That common shape lives here, so a family can inherit the machinery without also
inheriting another family's claims. `ForgottenAwaitGateStatements` used to be
both, and a family that only wanted a trustworthy child had to subclass it and
carry four public steps that were false for it.

Nothing in this class names a probe, a warning class or an expected sentence.
`ChildPytestRun` holds the mechanics of getting a trustworthy child;
`ChildPytestReport` reads its report as structured values.
"""

from pathlib import Path

from statements.child_pytest_report import ChildPytestReport
from statements.child_pytest_run import BACKEND_ROOT, PROJECT_CONFIG, ChildPytestRun


class ChildProbeStatements:
    """Run a probe suite under this project's pytest configuration and read it."""

    def __init__(self, keep_ambient_environment: bool = False) -> None:
        """Threaded through rather than re-decided, so there is one place to read.

        A family that says nothing gets the scrubbed child every claim about
        `pyproject.toml` depends on; the one family whose subject *is* the ambient
        environment opts in explicitly. See `ChildPytestRun.__init__`.
        """
        self._run = ChildPytestRun(keep_ambient_environment)
        self._report: ChildPytestReport | None = None

    def run_the_probe_under_the_projects_own_pytest_configuration(self) -> None:
        self._report = self._run.execute()

    def assert_the_projects_own_configuration_was_in_force(self) -> None:
        """Without this, a child that silently found no config proves nothing.

        pytest falls back to built-in defaults when `-c` cannot be read, and a
        defaults-only run passes any probe for a reason that has nothing to do
        with what this repository declares. Both header lines are pinned as whole
        values in one mapping: a substring check would also accept a `rootdir:`
        that merely starts with this path, and asserting the two separately would
        let the first mismatch hide the second.
        """
        child = self._child()
        expected = {"rootdir": str(BACKEND_ROOT), "configfile": PROJECT_CONFIG.name}
        actual = child.header_values(tuple(expected))
        assert actual == expected, (
            f"the child run's header reported {actual}, expected {expected} -- a run that fell "
            f"back to pytest's built-in defaults says nothing about the configuration "
            f"this repository actually declares:\n{child.tail}"
        )

    def assert_the_probe_suite_failed(self) -> None:
        self._assert_the_child_reported(1, {"failed": 1})

    def assert_the_probe_suite_passed(self) -> None:
        """The control that makes a failing probe attributable to its defect.

        Exactly one passed and nothing else: a warning counted here would mean the
        control is not clean, and a skip would mean pytest declined to run the
        probe's test at all rather than running it green -- which is how an
        `async def` probe fails silently when the async plugin is not loaded.
        """
        self._assert_the_child_reported(0, {"passed": 1})

    def _write_probe(self, tmp_path: Path, source: str) -> None:
        self._run.write_probe(tmp_path, source)

    def _no_child_was_run(self) -> bool:
        """Whether the act got as far as executing a child at all.

        Read by the families whose act is *guarded*: their refusal test asserts a
        message, and a message alone cannot tell a guard that short-circuited from
        one that ran a real child and then raised the same sentence -- which is the
        only property those guards exist for, since the whole cost of running under
        an unchosen environment is paid inside that child.
        """
        return self._report is None

    def _assert_the_child_reported(self, exit_code: int, counts: dict[str, int]) -> None:
        child = self._child()
        assert child.exit_code == exit_code, (
            f"the child pytest exited {child.exit_code}, expected {exit_code}:\n{child.tail}"
        )
        summarised = child.summary_counts()
        assert summarised == counts, (
            f"the child pytest summarised {summarised}, expected {counts} -- the "
            f"whole tally is pinned so a second failure, a skip or a stray warning cannot "
            f"hide inside a substring match:\n{child.tail}"
        )

    def _assert_the_failure_was_charged_to(
        self, expected: set[str], expected_text: str, because: str
    ) -> None:
        """Which tests failed, and that they failed for the stated reason.

        The set of failing names is compared whole rather than searched, so the
        assertion says both which test was charged and which were not, and cannot
        pass over an absent FAILURES section.

        `expected_text` is looked for in that section rather than anywhere in the
        output, because the sentences these families care about also appear in a
        child's *warnings summary* on precisely the runs they exist to reject --
        so an unscoped search would be satisfied by the rejected state, leaving
        the exit code as the only real assertion. `because` is the calling
        family's one-line reading of what a missing sentence would mean, since
        that is the part a reader meeting this failure in CI cannot reconstruct.
        """
        child = self._child()
        failing = child.failing_test_names()
        assert failing == expected, (
            f"the child's FAILURES section is about {failing or 'no test at all'}, expected "
            f"exactly {expected} -- the failing set is compared whole, so neither an extra "
            f"failure nor an absent section can pass:\n{child.tail}"
        )
        assert child.failure_text_contains(expected_text), (
            f'{because}: no "{expected_text}" in its FAILURES section:\n{child.tail}'
        )

    # Not `arranged()`: that helper's message tells the reader to call a `given_*`
    # step, and the step that sets this one is the act step, not an arrangement.
    def _child(self) -> ChildPytestReport:
        assert self._report is not None, "the probe must be run before it is asserted on"
        return self._report
