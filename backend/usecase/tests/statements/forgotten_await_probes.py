"""The two probe modules the forgotten-await gate runs as a child suite.

Kept apart from the Statements that runs them so neither file has to carry both
the source of a test suite and the machinery for reading one.

`gc.collect()` in each probe body is load-bearing. The `RuntimeWarning` behind a
forgotten `await` is emitted from the coroutine's `__del__`, so pytest attributes
it to whichever test happens to be running when the collector fires. Forcing the
collection inside the probe's own body pins the attribution instead of leaving it
to the interpreter's timing.
"""

PROBE_MODULE_NAME = "test_forgotten_await_probe.py"
PROBE_TEST_NAME = "test_probe"
PROBE_STEP_NAME = "given_an_arrangement_that_must_be_awaited"

# The defect, written as the smallest thing that reproduces it: an `async` step
# whose call site dropped the `await`. The arrangement never runs, and the only
# trace is a warning emitted from the coroutine's destructor.
FORGOTTEN_AWAIT_PROBE = f"""
import gc


async def {PROBE_STEP_NAME}() -> None:
    return None


def {PROBE_TEST_NAME}() -> None:
    {PROBE_STEP_NAME}()
    gc.collect()
"""

# The same module with the `await` in place. Its job is to prove the child run
# reports a pass when nothing is wrong, so a failure in the probe above is
# attributable to the forgotten `await` rather than to this machinery.
AWAITED_PROBE = f"""
import gc


async def {PROBE_STEP_NAME}() -> None:
    return None


async def {PROBE_TEST_NAME}() -> None:
    await {PROBE_STEP_NAME}()
    gc.collect()
"""

UNAWAITED_COROUTINE_TEXT = f"coroutine '{PROBE_STEP_NAME}' was never awaited"
