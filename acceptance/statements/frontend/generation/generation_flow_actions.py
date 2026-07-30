"""The two gestures every story-18 create-flow scenario begins with.

Scenario 1.1 (the type pick lands on the composer, and the send starts exactly one run) and
scenario 1.2 (a run in flight shows a generating state) drive the identical opening: pick the
doklad type card, then type a topic and send it. They diverge only in what they assert
afterwards. Both gestures used to live on `GenerateFlowStatements`, which left 1.2 a choice
between copying them and inheriting an unrelated scenario's assertions.

The workspace-shell locator and the create-endpoint path live here for the same reason — both
scenarios read them, and a second definition is a second place to fix a rename.

Mixed into a `BaseFrontendStatements` subclass, which supplies `navigate_to_doklad_type_modal`
and `_wait_for_visible`.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from statements.frontend.base_frontend_statements import WAIT_TIMEOUT_SECONDS
from statements.frontend.generation.composer_locators import TOPIC_INPUT, TOPIC_SEND_BUTTON

# The workspace shell — rendered by ChatWorkspace for EVERY generation state, unlike the
# breadcrumb (idle only) or the composer. That makes it the honest "did we leave the landing"
# probe: if this is absent, the flow never reached the workspace at all. In a non-idle state it
# also carries the Progress view, so its text is the panel-side generating indicator.
CHAT_PANEL = (By.CSS_SELECTOR, "[data-testid='chat-panel']")

GENERATIONS_PATH = "/api/v1/generations"


def is_status_poll_path(path: str) -> bool:
    """A status poll is GET {GENERATIONS_PATH}/<one segment> and nothing else.

    `_matching_requests_to` matches a URL SUBSTRING, so the collection load
    `GET /api/v1/generations` (a history list, no run id) lands in the same batch as a real
    poll. Filtering by SHAPE before asserting cardinality is what stops an unrelated feature's
    list request from failing a scenario with a message about the client's polling —
    the assertion would be reporting a healthy client as a broken one.

    Shared: scenario 1.2 asserts a poll IS on the wire, scenario 2.1 asserts the polls STOPPED
    once the editor opened. Both need the same shape test, and a second copy is a second place
    for the collection-load exclusion to be forgotten.
    """
    prefix = f"{GENERATIONS_PATH}/"
    if not path.startswith(prefix):
        return False
    remainder = path[len(prefix) :]
    return bool(remainder) and "/" not in remainder


class GenerationFlowActionsMixin:
    """Pick a document type, then send a topic — the create flow up to the run starting."""

    def pick_document_type_for_doklad(self, driver: WebDriver, app_url: str) -> None:
        # navigate_to_doklad_type_modal is the shared "click the CTA, then pick the doklad
        # type card" entry point — exactly the spec's "When they pick a document type". A live
        # session is required because the surface it lands on calls the API, which the backend
        # answers with 401 for a seeded token (collapsing the flow back to the landing).
        self.navigate_to_doklad_type_modal(driver, app_url, live_session=True)

    def send_topic(self, driver: WebDriver, topic: str) -> None:
        """Type the topic and send it. Pure action — the outcome is asserted separately.

        The send button is `disabled={!topic.trim()}` and Chrome discards a click on a
        disabled element SILENTLY — no exception. Waiting on visibility alone would let any
        lag before React's controlled re-render produce a test that typed a topic and clicked
        nothing. So the click waits for clickability: that wait guards the GESTURE (the button
        was actually pressable when we pressed it), not the scenario-level claim that a run
        began — which is `assert_send_started_a_run`'s job, stated in the test body.
        """
        self._wait_for_visible(driver, TOPIC_INPUT).send_keys(topic)
        WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(
            ec.element_to_be_clickable(TOPIC_SEND_BUTTON),
            "expected the send button to become enabled once a topic was typed, but it stayed disabled",
        ).click()

    def assert_send_started_a_run(self, driver: WebDriver) -> None:
        """The UI left the idle branch — the send was accepted, not swallowed.

        ChatWorkspace swaps Composer for Progress the moment a generation exists, so a
        still-present topic input means the submit never took. Keeping this out of `send_topic`
        makes the claim visible in the test body instead of hiding a Then inside a When, and
        distinguishes a swallowed click from a genuinely broken submit handler.
        """
        self._assert_not_visible(
            driver,
            TOPIC_INPUT,
            "expected sending a topic to replace the composer with the generation progress view, "
            "but the topic input is still shown — the send did not start a run",
        )
