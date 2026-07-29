"""Selenium DSL for story 18, scenario 2.1 — a completed generation opens in the editor.

Given the user is watching a generation complete
When the text becomes ready
Then the surface becomes the editor with the generated content loaded
And the user made no extra click to get there
"""

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from statements.frontend.base_frontend_statements import BaseFrontendStatements
from statements.frontend.generation.auto_editor_transition_expectations import (
    ARM_INTERACTION_WATCH_SCRIPT,
    AUTO_TRANSITION_TIMEOUT_SECONDS,
    EXPECTED_AUTO_EDITOR_BREADCRUMB,
    EXPECTED_GENERATED_TEXT,
    READ_INTERACTION_WATCH_SCRIPT,
)
from statements.frontend.generation.generating_state_locators import (
    DOC_BODY,
    DOC_ERROR,
    GENERATING_SURFACE,
)
from statements.frontend.generation.generation_flow_actions import GenerationFlowActionsMixin
from statements.frontend.generation.manual_editor_statements import (
    EDITABLE_CONTENT,
    EDITOR_BREADCRUMB,
    MANUAL_EDITOR,
)


class AutoEditorTransitionStatements(GenerationFlowActionsMixin, BaseFrontendStatements):
    """Send a topic, then watch the editor arrive by itself."""

    def watch_for_any_further_user_gesture(self, driver: WebDriver) -> None:
        """Arm the "no extra click" half of the scenario so it can be ASSERTED, not assumed.

        Without this the second Then is only a property of how the test happens to be written —
        "we did not call click(), so no click happened" — which pins nothing about the product
        and would keep passing if a `Открыть в редакторе` button were added and the test were
        later updated to press it. Recording trusted events makes the claim an observation: the
        browser itself reports whether the user did anything between the send and the editor.

        Armed AFTER the send, because the send IS a user gesture and a legitimate one. The gap
        between the two is a single WebDriver command in which nothing touches the page.
        """
        driver.execute_script(ARM_INTERACTION_WATCH_SCRIPT)

    def assert_editor_opened_by_itself(self, driver: WebDriver) -> None:
        """The editor appears, and it appears with no gesture from the user.

        Both halves in one method on purpose: the interaction count is only meaningful for the
        window that ends when the editor is up, so reading it before the wait would prove
        nothing and reading it in a separate test step would invite the two to drift apart.
        """
        WebDriverWait(driver, AUTO_TRANSITION_TIMEOUT_SECONDS).until(
            ec.visibility_of_element_located(MANUAL_EDITOR),
            "expected a completed generation to become the editor by itself, but "
            f"{MANUAL_EDITOR[1]} never appeared within "
            f"{AUTO_TRANSITION_TIMEOUT_SECONDS}s",
        )
        # Not just "an editor" — THE editor for the type this run picked. The shell alone is
        # satisfied by an editor opened for the wrong document type, or by one whose header
        # never resolved; the breadcrumb is what carries that identity.
        self._assert_element_text_equals(
            driver, EDITOR_BREADCRUMB, EXPECTED_AUTO_EDITOR_BREADCRUMB, "editor breadcrumb"
        )

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

    def assert_the_read_only_result_was_replaced(self, driver: WebDriver) -> None:
        """The surface BECAME the editor — the read-only completed view is not what is shown.

        `doc-body` is the markdown render of a finished generation. If it is still up, the
        product has a completed generation on screen that the user must do something with,
        which is exactly the extra step this scenario removes. Without this the editor could
        satisfy the assertion above while sitting somewhere else on the page.

        All three non-editor surfaces are ruled out, not just the successful one.
        `generating_state_locators.py` defines `doc-body` and `doc-error` as a pair, and an error
        surface left standing under an open editor is its own defect: the run failed, the editor
        holds whatever it holds, and the user is shown a success and a failure at once.

        `generation-generating` is ruled out for the mirror-image reason. An auto-transition that
        opens the editor without tearing the run down leaves the spinner standing underneath it,
        so the user is told the text is still being written while already holding it — and the
        poll loop that outlived its own result keeps calling the backend. Absent this the test
        passes on exactly that leak.
        """
        self._assert_not_visible(
            driver,
            DOC_BODY,
            "expected the completed generation to be REPLACED by the editor, but the read-only "
            f"result surface {DOC_BODY[1]} is still shown",
        )
        self._assert_not_visible(
            driver,
            DOC_ERROR,
            f"expected no failure surface once the editor is open, but {DOC_ERROR[1]} is shown "
            "— the run reported an error and the editor opened over it",
        )
        self._assert_not_visible(
            driver,
            GENERATING_SURFACE,
            f"expected the run to be torn down once the editor is open, but {GENERATING_SURFACE[1]}"
            " is still shown — the user is told the text is still being written while already "
            "holding it, and the poll loop outlived its own result",
        )

    def assert_editor_holds_the_generated_text(self, driver: WebDriver) -> None:
        """The editor opened LOADED — with this generation's text, not empty and not a placeholder.

        Pinned by equality against the whole fake provider output, because an editor that opens
        blank satisfies every other assertion in this test: the transition would be there and
        the user's document would not.

        The comparison is character-exact THROUGH the document, including the blank lines that
        separate the doklad's sections. See EXPECTED_GENERATED_TEXT for why the editor's
        inline-only schema leaves exactly one faithful rendering of those breaks, which makes
        this a decision the test gets to fix rather than one it has to wait on. Only the outer
        edges are stripped, matching `_assert_element_text_equals`, this lane's shared text
        comparison: `.text` is browser-normalized innerText, so its leading/trailing whitespace
        carries no product meaning and pinning it would buy flakiness rather than strictness.

        And the surface is asserted EDITABLE, not merely populated. "The surface becomes the
        editor" is not satisfied by a read-only render of the same text under the same testid —
        that is the completed view wearing the editor's name, and needing one more action to
        start typing is exactly the extra step this scenario removes.
        """
        editor = self._wait_for_visible(driver, EDITABLE_CONTENT)
        actual = editor.text.strip()
        assert actual == EXPECTED_GENERATED_TEXT, (
            f"expected the editor to open loaded with the generated text, got '{actual}'"
        )
        editable = editor.get_attribute("contenteditable")
        assert editable == "true", (
            "expected the generated text to land in an EDITABLE surface, but "
            f"{EDITABLE_CONTENT[1]} reports contenteditable='{editable}' — the user was handed a "
            "read-only render of their document, not the editor"
        )
