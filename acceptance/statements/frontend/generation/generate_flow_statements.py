from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from statements.frontend.base_frontend_statements import BaseFrontendStatements, WAIT_TIMEOUT_SECONDS
from statements.frontend.generation.composer_locators import (
    EXPECTED_SEND_BUTTON_TEXT,
    EXPECTED_TOPIC_INPUT_PLACEHOLDER,
    TOPIC_INPUT,
    TOPIC_SEND_BUTTON,
)
from statements.frontend.generation.mode_modal_statements import MODE_MODAL

# Story 18 unifies the create flow: picking a document type no longer opens a mode-select
# modal, it goes STRAIGHT to the generation surface — the topic composer, where the run is
# started. "Immediately" in the spec means the mode step is gone, not that a POST fires at
# type-pick time: the composer IS the topic source, and there is no topic to generate from
# until the user supplies one (an empty-topic POST is a backend 422). Confirmed against
# story 01's own mockup 04, which has always put topic entry after the type pick.
GENERATION_BREADCRUMB = (By.CSS_SELECTOR, "[data-testid='generation-breadcrumb']")
GENERATIONS_PATH = "/api/v1/generations"

# The wire shape of the create call, read off generationApi.createGeneration. `document_type`
# is the Cyrillic wire value ("доклад"), NOT the app value ("doklad") — the backend rejects the
# latter with 422 INVALID_DOCUMENT_TYPE, so asserting it here is what pins that the picked type
# actually reaches the request rather than being defaulted or dropped on the way.
EXPECTED_WIRE_DOCUMENT_TYPE = "доклад"
EXPECTED_VOLUME_PAGES = 5


class GenerateFlowStatements(BaseFrontendStatements):
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

    def send_topic(self, driver: WebDriver, topic: str) -> None:
        self._wait_for_visible(driver, TOPIC_INPUT).send_keys(topic)
        self._wait_for_visible(driver, TOPIC_SEND_BUTTON).click()

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
            driver, GENERATION_BREADCRUMB, "Доклад", "generation breadcrumb"
        )

        topic_input = self._wait_for_visible(driver, TOPIC_INPUT)
        placeholder = topic_input.get_attribute("placeholder")
        assert placeholder == EXPECTED_TOPIC_INPUT_PLACEHOLDER, (
            f"expected topic input placeholder '{EXPECTED_TOPIC_INPUT_PLACEHOLDER}', got '{placeholder}'"
        )
        value = topic_input.get_attribute("value")
        assert value == "", f"expected topic input to start empty, got '{value}'"

        self._assert_element_text_equals(
            driver, TOPIC_SEND_BUTTON, EXPECTED_SEND_BUTTON_TEXT, "send button text"
        )
        self._assert_disabled(driver, TOPIC_SEND_BUTTON, "send button")

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
        """
        requests = self._matching_requests_to(driver, GENERATIONS_PATH)

        assert len(requests) == 1, (
            f"expected exactly one POST {GENERATIONS_PATH}, got {len(requests)}"
        )

        body = self._request_body(requests[0], f"POST {GENERATIONS_PATH}")
        assert body == {
            "document_type": EXPECTED_WIRE_DOCUMENT_TYPE,
            "topic": topic,
            "volume_pages": EXPECTED_VOLUME_PAGES,
        }, f"unexpected POST {GENERATIONS_PATH} body: {body}"
