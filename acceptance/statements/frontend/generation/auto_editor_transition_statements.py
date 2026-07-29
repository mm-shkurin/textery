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
    AUTO_TRANSITION_TIMEOUT_SECONDS,
    EXPECTED_AUTO_EDITOR_BREADCRUMB,
    EXPECTED_GENERATED_TEXT,
)
from statements.frontend.generation.auto_editor_transition_wire_statements import (
    AutoEditorTransitionWireMixin,
)
from statements.frontend.generation.auto_editor_transition_witness import (
    NoExtraClickWitnessMixin,
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
    LOADING_SKELETON,
    MANUAL_EDITOR,
)
from statements.frontend.network_throttle_mixin import NetworkThrottleMixin


class AutoEditorTransitionStatements(
    GenerationFlowActionsMixin,
    NoExtraClickWitnessMixin,
    AutoEditorTransitionWireMixin,
    NetworkThrottleMixin,
    BaseFrontendStatements,
):
    """Send a topic, then watch the editor arrive by itself."""

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
        # The shell is NOT the chunk. `manual_editor_statements.LOADING_SKELETON` renders INSIDE
        # `[data-testid='manual-editor']`, so the wait above is satisfied while Tiptap +
        # ProseMirror — the largest bundle in the app, fetched at exactly this moment — is still
        # in flight. Every assertion after this point (the breadcrumb, the content) falls back to
        # the shared 5s WAIT_TIMEOUT_SECONDS, so a slow chunk fetch would fail on
        # `editor-content-area` and green would read that as "the conversion produced no text" —
        # the misattributed failure this lane keeps paying to eliminate. The chunk gets the
        # budget AUTO_TRANSITION_TIMEOUT_SECONDS was raised for in the first place, here, where
        # it is actually spent.
        WebDriverWait(driver, AUTO_TRANSITION_TIMEOUT_SECONDS).until(
            ec.invisibility_of_element_located(LOADING_SKELETON),
            "the editor shell mounted but its loading skeleton never cleared within "
            f"{AUTO_TRANSITION_TIMEOUT_SECONDS}s — the ManualEditor lazy chunk did not arrive, "
            "so nothing below this can speak about the transition",
        )
        # Not just "an editor" — THE editor for the type this run picked. The shell alone is
        # satisfied by an editor opened for the wrong document type, or by one whose header
        # never resolved; the breadcrumb is what carries that identity.
        self._assert_element_text_equals(
            driver, EDITOR_BREADCRUMB, EXPECTED_AUTO_EDITOR_BREADCRUMB, "editor breadcrumb"
        )

        self.assert_no_user_gesture_reached_the_page(driver)

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
        so the user is told the text is still being written while already holding it.

        That is ALL this method claims, and the claim used to be larger. It said it also caught
        the poll loop outliving its result; it cannot. Hiding the surface and calling
        `stopPolling()` are independent lines in `useGeneration.ts`, so an implementation that
        switches to the editor branch and forgets the teardown satisfies all three absence checks
        here while polling forever. The leak is caught on the wire, by
        `assert_the_poll_loop_stopped`.
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
        this a decision the test gets to fix rather than one it has to wait on. Compared through
        `_assert_element_text_equals`, this lane's shared text comparison, which strips only the
        outer edges: `.text` is browser-normalized innerText, so its leading/trailing whitespace
        carries no product meaning and pinning it would buy flakiness rather than strictness.

        And the surface is asserted EDITABLE, not merely populated. "The surface becomes the
        editor" is not satisfied by a read-only render of the same text under the same testid —
        that is the completed view wearing the editor's name, and needing one more action to
        start typing is exactly the extra step this scenario removes.
        """
        editor = self._assert_element_text_equals(
            driver, EDITABLE_CONTENT, EXPECTED_GENERATED_TEXT, "the text the editor opened with"
        )
        editable = editor.get_attribute("contenteditable")
        assert editable == "true", (
            "expected the generated text to land in an EDITABLE surface, but "
            f"{EDITABLE_CONTENT[1]} reports contenteditable='{editable}' — the user was handed a "
            "read-only render of their document, not the editor"
        )
