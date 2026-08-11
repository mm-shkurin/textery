"""How far the forgotten-await gate's child run actually reaches.

The gate proves "a bare run of a probe module under this configuration file fails
a forgotten `await`". Three things stand between that and the claim a reader takes
from it. Each was a sentence in a docstring before this file existed; each is an
assertion here now, and the third is still only half closed.

* How far the child's conftest walk reaches. pytest walks conftests upward from
  the *collected file*, not from rootdir, and the probe is written outside the
  repository -- so an unpinned walk does not stop at the repository either, it
  runs past it to the filesystem root. That is the wrong reach in both directions:
  a repository conftest that touched `warnings` would never reach the child, and
  any conftest that happened to sit above the scratch would. `--confcutdir` at the
  probe's own directory is what bounds it, and a poisoned conftest one level above
  the probe is what proves the bound is really there rather than merely passed.
* Where the probe may be written. "written outside `rootdir`, so the parent never
  collects it" rests on `tmp_path` landing outside the repository, and a CI image
  pointing `TMP` at the workspace -- or a plain `--basetemp` at `<repo>/.tmp` --
  breaks that without touching a line of configuration, leaving a collectable
  `test_*.py` behind for three runs under a fixed module name. The refusal is
  anchored to the repository now, matching its own remedy clause, and both trees it
  used to disagree about are exercised: a destination under `backend/` and one under
  the repository root but outside `backend/`. Each carries its own expected sentence,
  so neither arm has to go dark when the other's expectation moves.
* Which test an unraisable is charged to. It fires at garbage-collection time, so
  the run that fails is whichever one the collector lands in. `error::RuntimeWarning`
  alone could never misattribute; the second filter entry introduced a failure class
  that can. The leak is pinned here to the test that committed it.
"""

from pathlib import Path

from statements.arranged import arranged
from statements.forgotten_await_gate_statements import ForgottenAwaitGateStatements
from statements.forgotten_await_probes import (
    ATTRIBUTION_LEAKING_TEST_NAME,
    ATTRIBUTION_PROBE,
    PROBE_MODULE_NAME,
)
from statements.probe_destinations import (
    EXPECTED_REPOSITORY_REFUSAL,
    IN_REPOSITORY_SCRATCH,
    IN_TREE_SCRATCH,
    NO_PROBE_SOURCE,
    REPOSITORY_ROOT,
    remove_only_a_scratch_of_ours,
)

# A conftest placed one directory *above* the probe. Importing it is fatal, which
# is the whole design: a child that reaches it cannot fail quietly, and a child
# whose conftest walk is cut at the probe directory never sees it.
POISONED_CONFTEST_MESSAGE = "the child pytest walked its conftest search past the probe directory"
POISONED_CONFTEST_SOURCE = f'raise RuntimeError("{POISONED_CONFTEST_MESSAGE}")\n'


class GateReachStatements(ForgottenAwaitGateStatements):
    """The gate's own machinery, asserted on rather than assumed."""

    def __init__(self) -> None:
        super().__init__()
        self._refusal: AssertionError | None = None
        # The sentence *this* destination's write must be refused with, recorded by
        # the attempt step. Held per destination rather than hardcoded in the shared
        # assertion: when the expectation moved to a single re-anchored constant, the
        # backend-tree arm could only be kept green by skipping it, and a previously
        # passing guard went dark for the duration. Carried alongside the attempt,
        # both arms stay live whatever either one expects.
        self._expected_refusal: str | None = None
        # Not `False`: a default that reads as "nothing landed" is the answer the
        # assertion wants, so an attempt step that never ran would satisfy it.
        self._probe_landed: bool | None = None

    def given_a_conftest_above_the_probe_directory(self, tmp_path: Path) -> None:
        """The poisoned conftest, then the ordinary defective probe beneath it."""
        (tmp_path / "conftest.py").write_text(POISONED_CONFTEST_SOURCE, encoding="utf-8")
        self.given_a_call_site_that_forgets_to_await_an_async_given_step(tmp_path / "probe")

    def given_a_probe_whose_leak_is_in_one_test_and_whose_next_test_is_clean(
        self, tmp_path: Path
    ) -> None:
        self._write_probe(tmp_path, ATTRIBUTION_PROBE)

    def try_to_write_a_probe_inside_the_backend_tree(self) -> None:
        """The write that must be refused, attempted for real.

        Attempted rather than asserted about the path: the refusal has to sit
        *before* the write, or a CI image with `TMP` in the workspace has already
        dropped the file by the time anything notices.
        """
        self._try_to_write_a_probe_to(IN_TREE_SCRATCH, EXPECTED_REPOSITORY_REFUSAL)

    def try_to_write_a_probe_inside_the_repository_but_outside_the_backend_tree(self) -> None:
        """The destination that separates the anchor from the claim.

        The destination the anchor and the message used to disagree about, and the
        only one that can tell a repository-anchored guard from a `backend/`-anchored
        one -- the other refusal test aims at a path already under `backend/` and
        passes either way. `<repo>/.tmp` is not a hypothetical: it is what a
        `--basetemp` or a CI image with `TMP` at the workspace root produces, and it
        satisfies the guard while leaving a collectable `test_*.py` behind for any
        run scoped at the repository root rather than at `backend/`.
        """
        self._try_to_write_a_probe_to(IN_REPOSITORY_SCRATCH, EXPECTED_REPOSITORY_REFUSAL)

    def _try_to_write_a_probe_to(self, scratch: Path, expected_refusal: str) -> None:
        """Attempt, record what reached disk, and remove the scratch however it ended.

        The `finally` is not tidiness. Until the refusal is re-anchored the write
        for the out-of-backend destination genuinely lands, and a leftover
        `test_*_probe.py` at the repository root is collected by the next run --
        which is precisely the damage this test exists to prove is possible.

        Which is also why the probe's existence is read *before* the `rmtree` and
        kept. The `finally` destroys the only evidence for the "before it landed"
        half of the claim, and a guard moved to after `write_text` -- the exact
        regression `ChildPytestRun.write_probe`'s docstring warns about -- raises
        the same `AssertionError` with the file already on disk. Read afterwards
        the two are indistinguishable; read here they are not.
        """
        probe_path = scratch / PROBE_MODULE_NAME
        self._expected_refusal = expected_refusal
        try:
            self._write_probe(scratch, NO_PROBE_SOURCE)
        except AssertionError as refused:
            self._refusal = refused
        finally:
            self._probe_landed = probe_path.exists()
            remove_only_a_scratch_of_ours(scratch)
        assert not scratch.exists(), (
            f"{scratch} survived the removal that was supposed to take it away. On Windows "
            f"`ignore_errors=True` swallows the PermissionError an antivirus scanner or an "
            f"editor indexer produces on a directory it has open, so the scratch is left "
            f"inside the repository behind a fully green run -- and the next root-scoped run "
            f"collects whatever `test_*.py` is in it, which is the damage this test exists "
            f"to prove is possible"
        )

    def assert_the_write_was_refused_before_it_landed(self) -> None:
        assert self._refusal is not None, (
            f"a probe was written under {REPOSITORY_ROOT}, and nothing objected. The gate's "
            f"claim that the parent suite never collects the probe rests on the probe living "
            f"outside the repository, which is a sentence in a docstring rather than a check "
            f"-- a runner pointing TMP at the workspace satisfies the sentence and breaks the "
            f"claim, and the leftover module is collected by the real suite for three runs"
        )
        assert self._probe_landed is False, (
            "the write was refused, but the probe was already on disk when it was -- so the "
            "guard sits after `write_text` rather than before it. The refusal is then only a "
            "report: the `test_*.py` exists, and whether the parent collects it depends on "
            "something happening to delete it again, which is the claim's whole content"
        )
        expected = arranged(self._expected_refusal, "the expected refusal for this destination")
        actual = str(self._refusal)
        assert actual == expected, (
            f"the refusal read '{actual}', expected '{expected}' -- the reader "
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
