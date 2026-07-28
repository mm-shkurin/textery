from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from statements.frontend.base_frontend_statements import BaseFrontendStatements, WAIT_TIMEOUT_SECONDS
from statements.frontend.generation.composer_assertions import ComposerAssertionsMixin
from statements.frontend.generation.composer_locators import TOPIC_INPUT, TOPIC_SEND_BUTTON
from statements.frontend.generation.mode_modal_statements import MODE_MODAL

# Story 18 unifies the create flow: picking a document type no longer opens a mode-select
# modal, it goes STRAIGHT to the generation surface — the topic composer, where the run is
# started. "Immediately" in the spec means the mode step is gone, not that a POST fires at
# type-pick time: the composer IS the topic source, and there is no topic to generate from
# until the user supplies one (an empty-topic POST is a backend 422). Confirmed against
# story 01's own mockup 04, which has always put topic entry after the type pick.
GENERATION_BREADCRUMB = (By.CSS_SELECTOR, "[data-testid='generation-breadcrumb']")
GENERATIONS_PATH = "/api/v1/generations"

# The workspace shell — rendered by ChatWorkspace for EVERY generation state, unlike the
# breadcrumb (idle only) or the composer. That makes it the honest "did we leave the landing"
# probe: if these are absent, the flow never reached the workspace at all.
CHAT_PANEL = (By.CSS_SELECTOR, "[data-testid='chat-panel']")

# The frontend mints one Idempotency-Key per logical create (generationApi.createGeneration),
# and authorizedRequest replays the request VERBATIM — same key — on a 401. So a token expiry
# mid-flow puts two POSTs on the wire that the backend collapses onto ONE generation. Counting
# raw requests would call that correct behaviour double-billing; distinct keys is the count
# that actually tracks "how many generations were started".
IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"

# The wire shape of the create call, read off generationApi.createGeneration. `document_type`
# is the Cyrillic wire value ("доклад"), NOT the app value ("doklad") — the backend rejects the
# latter with 422 INVALID_DOCUMENT_TYPE, so asserting it here is what pins that the picked type
# actually reaches the request rather than being defaulted or dropped on the way.
EXPECTED_WIRE_DOCUMENT_TYPE = "доклад"
EXPECTED_VOLUME_PAGES = 5

# The breadcrumb's on-screen label for the picked type — the display casing ("Доклад"), which
# is neither the app value ("doklad") nor the wire value above. Named so the three do not get
# mistaken for one another at a glance.
EXPECTED_BREADCRUMB_TYPE_LABEL = "Доклад"


class GenerateFlowStatements(ComposerAssertionsMixin, BaseFrontendStatements):
    """Selenium DSL for the unified create flow (story 18, scenario 1.1).

    Picking a document type must land directly on the generation composer, with the
    story-5-era mode-select modal removed from the path entirely, and sending a topic
    must start exactly one generation carrying that topic and the picked type.
    """

    def pick_document_type_for_doklad(self, driver: WebDriver, app_url: str) -> None:
        # navigate_to_doklad_type_modal is the shared "click the CTA, then pick the doklad
        # type card" entry point — exactly the spec's "When they pick a document type". A live
        # session is required because the surface it lands on calls the API, which the backend
        # answers with 401 for a seeded token (collapsing the flow back to the landing).
        self.navigate_to_doklad_type_modal(driver, app_url, live_session=True)

    def assert_reached_generation_workspace(self, driver: WebDriver) -> None:
        """Precondition: the type pick left the landing and mounted the workspace at all.

        Asserted BEFORE any content check because the first failure is otherwise unreadable:
        a bare TimeoutException naming a CSS selector is produced identically by a dead live
        session (a 401 clears the token and collapses the app back to the landing), by a type
        pick that still routes to the mode step, and by a workspace that mounted in a
        non-idle state. Only the second of those is the RED this scenario predicts. The
        workspace shell renders in every generation state, so its absence means the flow
        never got here — and the URL is folded in to tell a collapse from a wrong route.
        """
        try:
            self._wait_for_visible(driver, CHAT_PANEL)
        except TimeoutException:
            raise AssertionError(
                "expected picking a document type to land on the generation workspace, but "
                f"{CHAT_PANEL[1]} never rendered; current URL '{driver.current_url}' — either the "
                "flow collapsed back to the landing (dead/rejected session) or the type pick still "
                "routes somewhere other than generation"
            ) from None

    def assert_no_generation_started_yet(self, driver: WebDriver) -> None:
        """Nothing has been billed at type-pick time — the claim this whole scenario defends.

        "Immediately" is the removal of the mode step, not a POST on the type card click. The
        final `exactly one` count would pass identically if the POST fired here and the send
        did nothing, so without this the design argument is only a comment.

        It doubles as the log-window fix: `driver.get_log` DRAINS the performance buffer, so
        this scan consumes the live register/verify/login round trip and the whole asset load,
        leaving the final scan a window containing only the send. Without it that final scan
        looks at everything since browser start and a chromedriver buffer eviction reports
        `got 0` for a healthy build.
        """
        requests = self._matching_requests_to(driver, GENERATIONS_PATH)

        assert not requests, (
            f"expected no POST {GENERATIONS_PATH} before a topic was sent, got {len(requests)}: "
            f"{[r.get('url') for r in requests]} — generation must start from the composer, "
            "not from the document-type click"
        )

    def send_topic(self, driver: WebDriver, topic: str) -> None:
        """Type the topic and send it, then confirm the click was actually accepted.

        The send button is `disabled={!topic.trim()}` and Chrome discards a click on a
        disabled element SILENTLY — no exception. Waiting on visibility alone would let any
        lag before React's controlled re-render produce a test that typed a topic, clicked
        nothing, and failed a second later on a request count of zero. So the click waits for
        clickability, and afterwards we pin that the UI left the idle branch: ChatWorkspace
        swaps Composer for Progress the moment a generation exists, so a still-present topic
        input means the submit never took — distinguishing a swallowed click from a genuinely
        broken submit handler.
        """
        self._wait_for_visible(driver, TOPIC_INPUT).send_keys(topic)
        WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(
            ec.element_to_be_clickable(TOPIC_SEND_BUTTON),
            "expected the send button to become enabled once a topic was typed, but it stayed disabled",
        ).click()
        WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(
            ec.invisibility_of_element_located(TOPIC_INPUT),
            "expected sending a topic to replace the composer with the generation progress view, "
            "but the topic input is still shown — the send did not start a run",
        )

    def assert_generation_surface_shown(self, driver: WebDriver) -> None:
        """The picked type is confirmed on screen and the composer is ready for a topic.

        Asserted instead of waiting on the transient pending state: the generating surface
        is reachable only after a topic is sent, and even then a fast backend can move past
        it between polls, which would look identical to a regression.

        Every element the scenario depends on is pinned to an exact value, not merely to
        being present: the breadcrumb names the type that was picked, the composer starts
        empty and prompts for a topic, and the send button is present but refuses to fire
        until there is one. Presence alone would pass on a composer wired to the wrong type
        or pre-filled with a stale topic.
        """
        self._assert_element_text_equals(
            driver, GENERATION_BREADCRUMB, EXPECTED_BREADCRUMB_TYPE_LABEL, "generation breadcrumb"
        )
        self._assert_topic_input_empty_and_prompting(driver)
        self._assert_send_button_idle(driver)

    def assert_no_mode_modal_shown(self, driver: WebDriver) -> None:
        WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(
            ec.invisibility_of_element_located(MODE_MODAL),
            "expected no mode-select modal after picking a type, but it was shown",
        )

    def assert_exactly_one_generation_started(self, driver: WebDriver, topic: str) -> None:
        """A positive assertion that the run actually began, with the right payload.

        Without this the modal-absence check above passes vacuously for any modal-free
        screen — the landing, an error, the editor. Counting the POST also pins that one
        send bills one generation rather than two.

        Count and payload are read from ONE log scan on purpose: `driver.get_log` drains
        the performance buffer, so a second helper call would see an empty log and report
        zero requests for a flow that made one.

        The count is over DISTINCT Idempotency-Keys, not raw requests: a 401 mid-flow makes
        authorizedRequest replay the POST verbatim, keeping the key createGeneration minted
        once, and the backend collapses the pair onto one generation. Counting requests
        would fail on that correct behaviour with the exact wording of the double-billing
        defect this story fought — an unreproducible flake reading as a real regression.
        Each key is printed so a replay is legible on sight.
        """
        requests = self._matching_requests_to(driver, GENERATIONS_PATH)

        keys = [self._request_header(request, IDEMPOTENCY_KEY_HEADER) for request in requests]
        assert None not in keys, (
            f"expected every POST {GENERATIONS_PATH} to carry an {IDEMPOTENCY_KEY_HEADER} header "
            f"so a 401 replay collapses server-side, got keys {keys}"
        )

        distinct_keys = set(keys)
        assert len(distinct_keys) == 1, (
            f"expected exactly one generation started (one distinct {IDEMPOTENCY_KEY_HEADER}), got "
            f"{len(distinct_keys)} across {len(requests)} POST {GENERATIONS_PATH} request(s) with "
            f"keys {keys}"
        )

        body = self._request_body(requests[0], f"POST {GENERATIONS_PATH}")
        assert body == {
            "document_type": EXPECTED_WIRE_DOCUMENT_TYPE,
            "topic": topic,
            "volume_pages": EXPECTED_VOLUME_PAGES,
        }, f"unexpected POST {GENERATIONS_PATH} body: {body}"
