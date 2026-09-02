from selenium.webdriver.remote.webdriver import WebDriver

from statements.frontend.base_frontend_statements import BaseFrontendStatements
from statements.frontend.generation.composer_assertions import ComposerAssertionsMixin
from statements.frontend.generation.generation_flow_actions import GENERATION_FORM


class ChatWorkspaceStatements(ComposerAssertionsMixin, BaseFrontendStatements):
    # Per known-debt #8, the standalone generation-form page (mockup 04) was replaced
    # by a single doc-left/chat-right screen; the "form fields" for scenario 4.1 are
    # now a single free-text composer in the chat panel, mapped to `topic` on submit.
    # The composer's locators and expected copy live in composer_locators, and the
    # assertions over them in composer_assertions, because the story-18 create flow
    # asserts the same composer.

    def navigate_to_chat_workspace_for_doklad(self, driver: WebDriver, app_url: str) -> None:
        """Reach the chat workspace: sign in, open the CTA, pick the doklad type.

        Story 7 put generation behind a session, so a logged-in precondition is required —
        `navigate_to_doklad_type_modal` establishes it via the base class's SEEDED grade
        (see `_establish_logged_in_precondition` for why a placeholder token is honest here).
        This class used to seed the session itself first; that copy was dead, because the base
        helper overwrote both storage keys moments later.

        The seeded token stays honest only while the API serves anonymous callers. Verified
        2026-07-16: `POST /api/v1/generations` still does. When that changes, this scenario
        needs `live_session=True` — a fake token passes the client gate and the real API refuses.

        Story 18 removed the mode-select modal: picking a type lands on step='form' directly,
        so the type click is the last navigation step — there is no mode card left to click.
        """
        self.navigate_to_doklad_type_modal(driver, app_url)

    def assert_generation_form_is_visible(self, driver: WebDriver) -> None:
        # `_wait_for_visible` waits on `visibility_of_element_located`, so the element it returns
        # is displayed by construction — a follow-up `assert element.is_displayed()` could never
        # fire, and its message could never be read. The wait's TimeoutException IS the failure.
        self._wait_for_visible(driver, GENERATION_FORM)

    def assert_topic_input_is_visible_and_empty(self, driver: WebDriver) -> None:
        self._assert_topic_input_empty_and_prompting(driver)

    def assert_send_button_is_visible_and_disabled(self, driver: WebDriver) -> None:
        self._assert_send_button_idle(driver)
