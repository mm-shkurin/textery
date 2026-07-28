import time
from urllib.parse import urlparse
from uuid import UUID

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from statements.frontend.base_frontend_statements import BaseFrontendStatements, WAIT_TIMEOUT_SECONDS
from statements.frontend.generation.generation_flow_actions import (
    CHAT_PANEL,
    GENERATIONS_PATH,
    GenerationFlowActionsMixin,
)
from statements.frontend.network_throttle_mixin import NetworkThrottleMixin

# The generating surface, marked with this testid by story 18 explicitly as scenario 1.2's
# subject. It renders only on DocArea's `pending` branch, so observing it observes exactly
# the generating state and nothing else.
GENERATING_SURFACE = (By.CSS_SELECTOR, "[data-testid='generation-generating']")

# The two terminal surfaces. Asserted ABSENT so "a generating state is shown" cannot be
# satisfied by a screen that has already moved on: without these the run could complete
# between the send and the check and the test would still be looking at a result it called
# progress.
DOC_BODY = (By.CSS_SELECTOR, "[data-testid='doc-body']")
DOC_ERROR = (By.CSS_SELECTOR, "[data-testid='doc-error']")

# The full visible text of each generating surface, read off the built components rather than
# a mockup. Pinned by equality, not substring: the doc area renders a placeholder in three of
# the four generation states and they differ only by their copy, so a presence-only check
# would pass on the idle placeholder — the one state that means the send never happened.
EXPECTED_GENERATING_DOC_TEXT = (
    "Готовим ваш доклад\nОбычно занимает 1–2 минуты — страница обновится автоматически"
)

# The left panel's Progress view. `ИИ пишет доклад` is rendered ONLY while pending — the
# completed and failed branches replace it — so this is the second, independent witness that
# the surface is the generating one. The typing-dots animation carries no text.
#
# The bare `✦` lines are each step's avatar (`Progress.ChatMsg`), which Selenium reports as its
# own line because avatar and bubble are separate block children. They are kept in the expected
# value rather than filtered out: `.text` is what the user sees, and the failed branch swaps the
# same glyph for `✕`, so dropping them would discard a signal instead of noise.
#
# `ХОД ГЕНЕРАЦИИ` is upper-case because `.chat-panel h3` carries `text-transform: uppercase` and
# Selenium reports RENDERED text — the source says `Ход генерации`. Worth stating: this is the
# one layer that can see it. jsdom applies no CSS, so the renderer-level suite asserts the
# source casing, and the two expected values legitimately differ for the same element.
EXPECTED_GENERATING_PANEL_TEXT = (
    "ХОД ГЕНЕРАЦИИ\n✦\nАнализирую тему и требования\n✦\nИИ пишет доклад"
)


class GeneratingStateStatements(
    GenerationFlowActionsMixin, NetworkThrottleMixin, BaseFrontendStatements
):
    """Selenium DSL for story 18, scenario 1.2 — a generating document shows progress.

    Given the user has started a generation
    When the result is not ready yet
    Then a generating state is shown
    """

    def hold_the_result_not_ready(self, driver: WebDriver) -> None:
        """Make the round trip slow enough that the generating state is deterministically observable.

        THE HAZARD THIS EXISTS FOR: the generating surface is transient. The acceptance stack
        runs `GENERATION_PROVIDER=fake`, whose `generate` returns a canned string with no
        latency at all, and `useGeneration.submit` fires its first status check the instant
        the create POST resolves — so on a healthy build the pending state can last single-digit
        milliseconds. A WebDriverWait polls every 500ms. Waiting on the surface unthrottled is
        therefore a coin flip whose failure is a TimeoutException indistinguishable from the
        real regression this scenario is meant to catch, and a green run would prove nothing
        about whether the state was ever shown.

        The fix is to widen the window rather than to retry into it. CDP latency holds every
        response open for `SLOW_LATENCY_MS`, and `submit` sets `pending` SYNCHRONOUSLY before
        awaiting the POST — so the generating state is up before the first byte leaves and
        stays up for at least the POST round trip plus the first status round trip, twice the
        latency. That is the scenario's own "When the result is not ready yet": the client has
        asked and has not been told.

        Deliberately not done by slowing the provider: that is production code, and a fake
        that sleeps would make every backend acceptance test pay for this one browser check.
        """
        self.throttle_network(driver)

    def release_the_result(self, driver: WebDriver) -> None:
        """Drop the latency so the run can finish. Every driver is torn down per test anyway;
        this keeps the throttle from outliving the one assertion that needs it."""
        self.clear_network_throttle(driver)

    def assert_generating_state_shown(self, driver: WebDriver) -> None:
        """Both halves of the split workspace say the run is in progress.

        The scenario line is one clause ("a generating state is shown") but the surface is
        two panels, and either one alone would leave the other free to say something else —
        a doc area promising a document beside a panel that has stopped reporting progress is
        exactly the perpetual-spinner ambiguity scenario 4.1 goes on to separate. Both are
        pinned to their exact copy.

        The status badge (`В обработке`) is the third generating indicator and is NOT asserted:
        it carries no data-testid, and class- and tag-based locators are forbidden. Left to the
        renderer-level suite, which already covers it.
        """
        self._assert_element_text_equals(
            driver, GENERATING_SURFACE, EXPECTED_GENERATING_DOC_TEXT, "generating doc surface"
        )
        self._assert_element_text_equals(
            driver, CHAT_PANEL, EXPECTED_GENERATING_PANEL_TEXT, "generation progress panel"
        )

    def assert_no_result_shown(self, driver: WebDriver) -> None:
        """Neither terminal surface is up — this is progress, not an outcome.

        Also the backstop for the throttle: if the latency were silently not applied the run
        could complete before the assertions above, and their failure message would blame the
        copy rather than the timing. A completed body found here names the real cause.
        """
        self._assert_not_visible(
            driver,
            DOC_BODY,
            "expected no generated document while the generation is still running, but "
            f"{DOC_BODY[1]} was shown",
        )
        self._assert_not_visible(
            driver,
            DOC_ERROR,
            "expected no failure panel while the generation is still running, but "
            f"{DOC_ERROR[1]} was shown",
        )

    def assert_client_is_awaiting_the_result(self, driver: WebDriver) -> None:
        """The generating state is a watched one: a status check is genuinely on the wire.

        Without this, every assertion above is satisfied by a spinner that will spin forever —
        `useGeneration` could have failed to start its poll and nothing on screen would differ.
        `Network.requestWillBeSent` fires when the request is issued, not when it answers, so
        this is observable while the call is still held open by the latency.

        Scanned in a loop rather than once, because the first status check cannot exist yet
        when the DOM assertions above finish: `useGeneration.submit` issues it only after the
        create POST resolves, and the throttle deliberately holds that POST open for
        SLOW_LATENCY_MS. A single scan would run inside that gap and report a healthy client
        as one that never polls. The loop ACCUMULATES because `driver.get_log` DRAINS the
        performance buffer — re-reading it is not idempotent, so a hit seen on an early pass
        would be invisible to a later one.
        """
        status_checks: list[dict] = []
        deadline = time.monotonic() + WAIT_TIMEOUT_SECONDS
        while not status_checks and time.monotonic() < deadline:
            status_checks += self._matching_requests_to(driver, GENERATIONS_PATH, method="GET")

        assert status_checks, (
            f"expected the client to be polling GET {GENERATIONS_PATH}/<id> while the generation "
            "runs, but no status request was issued — the generating state is not being watched "
            "and would never resolve"
        )

        # Presence of *a* GET is not the claim. `_matching_requests_to` matches on a URL
        # SUBSTRING, so a collection load (GET /api/v1/generations, no run id at all) satisfies
        # a truthiness check while no status poll exists — exactly the regression this method
        # says it catches. So the polled path is pinned by equality instead.
        polled_paths = {urlparse(request.get("url", "")).path for request in status_checks}
        assert len(polled_paths) == 1, (
            f"expected every status check to poll the one run that was just started, got "
            f"{len(polled_paths)} distinct paths {sorted(polled_paths)}"
        )

        polled_path = polled_paths.pop()
        generation_id = polled_path.rsplit("/", 1)[-1]
        assert polled_path == f"{GENERATIONS_PATH}/{generation_id}", (
            f"expected the client to poll GET {GENERATIONS_PATH}/<id>, got '{polled_path}' — a "
            "path with no single run id is a collection load, not a status check"
        )

        # The id itself is the one genuinely opaque value here: it is minted by the backend and
        # returned in the create POST's RESPONSE body, which `Network.requestWillBeSent` does not
        # carry — so there is no way to capture it for an equality check from the performance log.
        # Its FORMAT is not opaque, and pinning it is what rejects `/api/v1/generations/undefined`,
        # the shape a broken id hand-off actually produces.
        try:
            UUID(generation_id)
        except ValueError:
            raise AssertionError(
                f"expected the polled run id to be a UUID, got '{generation_id}' in "
                f"'{polled_path}' — the generation id was not threaded into the status poll"
            ) from None
