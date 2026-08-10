"""How far the forgotten-await gate's child run actually reaches.

The gate proves "a bare run of a probe module under this configuration file fails
a forgotten `await`". Three things stand between that and the claim a reader takes
from it, and all three are prose today rather than assertions.

* The child is launched with `--rootdir` but no `--confcutdir`. pytest walks
  conftests upward from the *collected file*, not from rootdir, and the probe is
  written outside the repository -- so the walk does not stop at the repository
  either, it runs past it to the filesystem root. Today that loads nothing,
  because nothing above the scratch happens to be a conftest. It is still the
  wrong reach in both directions: a repository conftest that touched `warnings`
  would never reach the child, and any conftest that appears above the scratch
  would.
* "written outside `rootdir`, so the parent never collects it" is a sentence in a
  docstring. If `tmp_path` ever lands inside the repository -- a CI image pointing
  `TMP` at the workspace -- the child imports the repository's conftests and the
  parent collects the leftover probe on a later run, since `tmp_path` roots
  survive three runs under a fixed module name.
* An unraisable warning fires at garbage-collection time, so the run that fails is
  whichever one the collector lands in. `error::RuntimeWarning` alone could never
  misattribute; the second filter entry introduced a failure class that can. What
  the gate must pin is that the leak is reported against the test that leaked.
"""

import shutil
from pathlib import Path

from statements.child_pytest_run import BACKEND_ROOT
from statements.forgotten_await_gate_statements import ForgottenAwaitGateStatements
from statements.forgotten_await_probes import (
    ATTRIBUTION_LEAKING_TEST_NAME,
    ATTRIBUTION_PROBE,
)

# A conftest placed one directory *above* the probe. Importing it is fatal, which
# is the whole design: a child that reaches it cannot fail quietly, and a child
# whose conftest walk is cut at the probe directory never sees it.
POISONED_CONFTEST_MESSAGE = "the child pytest walked its conftest search past the probe directory"
POISONED_CONFTEST_SOURCE = f'raise RuntimeError("{POISONED_CONFTEST_MESSAGE}")\n'

# Where the probe-path refusal is exercised. Inside the repository on purpose --
# that is the condition being refused -- and removed in a `finally`, because until
# the refusal lands the write actually happens, and a stray `test_*_probe.py`
# under `backend/` is collected by the real suite on the next run.
IN_TREE_SCRATCH = BACKEND_ROOT / "usecase" / "tests" / "harness" / "_gate_reach_scratch"

# Deliberately no probe body: the refusal must land on the path alone, before the
# source is ever looked at, so this write has nothing for a lenient guard to
# approve of. An empty literal at the call site would read as an oversight.
NO_PROBE_SOURCE = ""

# The refusal `ChildPytestRun.write_probe` must raise, decided here because the
# test is the specification -- GREEN writes the guard to this text, not the other
# way round. Compared whole rather than searched for the root path: a refusal
# raised for some other reason echoes the attempted path too, since the path is
# under `BACKEND_ROOT` by construction, so a substring check cannot tell the
# path-refusal apart from any other AssertionError on that write.
EXPECTED_IN_TREE_REFUSAL = (
    f"a probe may not be written under {BACKEND_ROOT}: the parent suite collects "
    f"`test_*.py` from that tree, so the probe survives as a real test of this suite "
    f"and the gate's claim that the parent never collects it becomes false. Write the "
    f"probe to a tmp_path outside the repository"
)


class GateReachStatements(ForgottenAwaitGateStatements):
    """The gate's own machinery, asserted on rather than assumed."""

    def __init__(self) -> None:
        super().__init__()
        self._refusal: AssertionError | None = None

    def given_a_conftest_above_the_probe_directory(self, tmp_path: Path) -> None:
        """The poisoned conftest, then the ordinary defective probe beneath it."""
        (tmp_path / "conftest.py").write_text(POISONED_CONFTEST_SOURCE, encoding="utf-8")
        self.given_a_call_site_that_forgets_to_await_an_async_given_step(tmp_path / "probe")

    def given_a_probe_whose_leak_is_in_one_test_and_whose_next_test_is_clean(
        self, tmp_path: Path
    ) -> None:
        self._write_probe(tmp_path, ATTRIBUTION_PROBE)

    def try_to_write_a_probe_inside_the_repository(self) -> None:
        """The write that must be refused, attempted for real.

        Attempted rather than asserted about the path: the refusal has to sit
        *before* the write, or a CI image with `TMP` in the workspace has already
        dropped the file by the time anything notices.
        """
        try:
            self._write_probe(IN_TREE_SCRATCH, NO_PROBE_SOURCE)
        except AssertionError as refused:
            self._refusal = refused
        finally:
            shutil.rmtree(IN_TREE_SCRATCH, ignore_errors=True)

    def assert_the_write_was_refused_before_it_landed(self) -> None:
        assert self._refusal is not None, (
            f"a probe was written under {BACKEND_ROOT}, and nothing objected. The gate's "
            f"claim that the parent suite never collects the probe rests on the probe living "
            f"outside the repository, which is a sentence in a docstring rather than a check "
            f"-- a runner pointing TMP at the workspace satisfies the sentence and breaks the "
            f"claim, and the leftover module is collected by the real suite for three runs"
        )
        actual = str(self._refusal)
        assert actual == EXPECTED_IN_TREE_REFUSAL, (
            f"the refusal read '{actual}', expected '{EXPECTED_IN_TREE_REFUSAL}' -- the reader "
            f"has to be told which tree the probe may not be written into and where to put it "
            f"instead, and any other AssertionError on that write must not be mistaken for it"
        )

    def assert_the_poisoned_conftest_was_never_imported(self) -> None:
        """The claim the conftest test is actually about, said out loud.

        Without this the test proves "the walk stopped" only inferentially, from
        the tally -- and a child that *did* import the conftest, blew up on it, and
        still reported one failure satisfies the tally. The poisoned conftest's own
        sentence appearing anywhere in the child's output is the direct evidence.
        """
        child = self._child()
        assert POISONED_CONFTEST_MESSAGE not in child.output, (
            f"the child's output carries '{POISONED_CONFTEST_MESSAGE}', so its conftest walk "
            f"ran past the probe directory. The probe lives outside the repository, so the "
            f"walk that reached this conftest would reach anything else sitting above the "
            f"scratch, and would never reach the repository's own:\n{child.tail}"
        )

    def assert_the_leak_was_reported_against_the_test_that_leaked(self) -> None:
        """The leaking test named, and -- in the same equality -- the clean one not.

        Delegated rather than recopied: the parent already compares the whole set
        of failing names, which is what makes the negative half real. Asserting
        `CLEAN not in failures` on its own would pass over an empty section, and an
        unraisable that fired late enough to be charged to the following test still
        puts the coroutine sentence in a FAILURES section.
        """
        self._assert_the_await_leak_was_charged_to({ATTRIBUTION_LEAKING_TEST_NAME})

    def assert_one_test_failed_and_the_other_passed(self) -> None:
        self._assert_the_child_reported(1, {"failed": 1, "passed": 1})
