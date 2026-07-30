"""The "and the user made no extra click" witness for story 18, scenario 2.1.

Split from `auto_editor_transition_statements.py` at the 200-line cap. The DOM assertions stay
there; the instrument that lets the scenario's second Then be ASSERTED rather than assumed
lives here, together with the throttle that makes its observation window real.
"""

from selenium.webdriver.remote.webdriver import WebDriver

from statements.frontend.generation.auto_editor_transition_expectations import (
    ARM_INTERACTION_WATCH_SCRIPT,
    READ_INTERACTION_WATCH_SCRIPT,
)
from statements.frontend.generation.generating_state_locators import GENERATING_SURFACE


class NoExtraClickWitnessMixin:
    """Arm, hold open, and read the trusted-event watch. Mixed into a BaseFrontendStatements."""

    def hold_the_run_pending(self, driver: WebDriver) -> None:
        """Widen the window the gesture watch is armed in, so it is provably non-empty.

        THE HAZARD THIS EXISTS FOR, and it is the same one scenario 1.2 fought: the acceptance
        stack's `FakeProvider.generate` returns a canned string with no latency, so a whole run
        can complete in single-digit milliseconds. `assert_send_started_a_run` is an INVISIBILITY
        wait on the composer — it returns as soon as the composer is gone and establishes
        nothing about whether the run is still pending. Unthrottled, the run can therefore
        finish and the transition can occur BEFORE `ARM_INTERACTION_WATCH_SCRIPT` runs: the
        watch then arms on the post-transition page, records nothing because there is nothing
        left to happen, and `events == []` passes having observed an EMPTY window. It defeats
        the reload check the same way — arm after a reload and `__acceptanceUserEvents` exists
        and is `[]`, so both assertions read clean on a page whose witness never watched
        anything.

        The original reasoning for skipping the throttle here ("2.1's subject is terminal, so
        waiting for the editor is not a race") was true of the SUBJECT and false of the
        INSTRUMENT: the arming window is exactly as transient as 1.2's subject was, and it is
        the thing that has to be caught. So the create POST is held open for the arm, and the
        throttle is dropped again immediately after (`let_the_run_finish`) so the remaining
        round trips and the ManualEditor chunk fetch pay nothing for it.
        """
        self.throttle_network(driver)

    def let_the_run_finish(self, driver: WebDriver) -> None:
        """Drop the latency the moment the watch is armed — the transition itself is not throttled."""
        self.clear_network_throttle(driver)

    def watch_for_any_further_user_gesture(self, driver: WebDriver) -> None:
        """Arm the "no extra click" half of the scenario so it can be ASSERTED, not assumed.

        Without this the second Then is only a property of how the test happens to be written —
        "we did not call click(), so no click happened" — which pins nothing about the product
        and would keep passing if a `Открыть в редакторе` button were added and the test were
        later updated to press it. Recording trusted events makes the claim an observation: the
        browser itself reports whether the user did anything between the send and the editor.

        Armed AFTER the send, because the send IS a user gesture and a legitimate one. The gap
        between the two is a single WebDriver command in which nothing touches the page.

        The generating surface is asserted up FIRST, and that assertion is what makes the whole
        witness mean anything: it proves the run has not finished, so the window the watch is
        about to open genuinely CONTAINS the transition. Without it an empty event list is
        equally consistent with "the user did nothing" and "the watch armed after everything had
        already happened", and the second reading is the one a zero-latency fake provider makes
        likely. Held open by `hold_the_run_pending`; see it for the full argument.

        Chosen over installing the script through CDP `Page.addScriptToEvaluateOnNewDocument`,
        which would also survive a reload: that only runs on a NEW document, so on the healthy
        in-place path it would never execute at all and the read would return `None` — turning
        the reload check into a permanent false failure — and it would additionally have to
        account for the send's own trusted click. Proving the window non-empty is the smaller
        mechanism that fixes the actual defect.
        """
        self._wait_for_visible(driver, GENERATING_SURFACE)
        driver.execute_script(ARM_INTERACTION_WATCH_SCRIPT)

    def assert_no_user_gesture_reached_the_page(self, driver: WebDriver) -> None:
        """Read the watch. Called from `assert_editor_opened_by_itself`, never from the test body.

        The count is only meaningful for the window that ENDS when the editor is up, so reading
        it as its own test step would invite the two to drift apart.
        """
        events = driver.execute_script(READ_INTERACTION_WATCH_SCRIPT)
        # A None here is not "no events": it means the page context was replaced (a full reload
        # or a real navigation), which would have discarded the watch — and an auto-transition
        # that reloads the page is not the transition this scenario describes. Fail on it
        # explicitly rather than let a lost witness read as a clean run.
        assert events is not None, (
            "the user-gesture watch is gone from the page, so the document was reloaded or "
            "navigated between the send and the editor — this transition is not the in-place "
            "one the scenario describes, and the no-extra-click claim is unverifiable"
        )
        assert events == [], (
            "expected the user to make NO extra gesture between sending the topic and the "
            f"editor opening, but the page received {events} — the editor was reached by "
            "interacting with something, not by the generation completing"
        )
