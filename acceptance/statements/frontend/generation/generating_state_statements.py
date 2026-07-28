import time
from urllib.parse import urlparse

from selenium.webdriver.remote.webdriver import WebDriver

from statements.frontend.base_frontend_statements import BaseFrontendStatements, WAIT_TIMEOUT_SECONDS
from statements.frontend.generation.generation_flow_actions import (
    CHAT_PANEL,
    GENERATIONS_PATH,
    GenerationFlowActionsMixin,
)
from statements.frontend.generation.generating_state_locators import (
    DOC_BODY,
    DOC_ERROR,
    EXPECTED_GENERATING_DOC_TEXT,
    EXPECTED_GENERATING_PANEL_TEXT,
    GENERATING_SURFACE,
)
from statements.frontend.network_throttle_mixin import SLOW_LATENCY_MS, NetworkThrottleMixin
from statements.uuid_format import is_uuid

# How long to keep scanning the performance log for the first status poll. It cannot be
# WAIT_TIMEOUT_SECONDS alone: that constant is tuned for DOM waits, while this event
# STRUCTURALLY cannot occur before the throttled create POST resolves — at least
# SLOW_LATENCY_MS. Deriving the budget from the latency ties the two constants together, so
# raising SLOW_LATENCY_MS can no longer turn a healthy client into a test that reports it
# never polls. Whichever is larger wins, so the DOM budget is still the floor.
POLL_SCAN_TIMEOUT_SECONDS = max(WAIT_TIMEOUT_SECONDS, 3 * SLOW_LATENCY_MS / 1000)


def _is_status_poll_path(path: str) -> bool:
    """A status poll is GET {GENERATIONS_PATH}/<one segment> and nothing else.

    `_matching_requests_to` matches a URL SUBSTRING, so the collection load
    `GET /api/v1/generations` (a history list, no run id) lands in the same batch as a real
    poll. Filtering by SHAPE before asserting cardinality is what stops an unrelated feature's
    list request from failing this scenario with a message about the client not polling —
    the assertion would be reporting a healthy client as a broken one.
    """
    prefix = f"{GENERATIONS_PATH}/"
    if not path.startswith(prefix):
        return False
    remainder = path[len(prefix) :]
    return bool(remainder) and "/" not in remainder


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

        Also the backstop for the throttle, and it is called BEFORE `assert_generating_state_shown`
        for that reason: if the latency were silently not applied the run would complete early and
        the generating-surface wait would raise a bare TimeoutException naming a CSS selector —
        the exact misattributed failure this scenario exists to eliminate. Ordered after it, this
        method could only ever run on a path where it had nothing left to catch. Ordered first, a
        completed body names the real cause. It costs nothing when the throttle IS applied: neither
        terminal surface can be up yet, so both checks pass immediately.
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
        polled_paths: set[str] = set()
        deadline = time.monotonic() + POLL_SCAN_TIMEOUT_SECONDS
        while not polled_paths and time.monotonic() < deadline:
            polled_paths |= {
                path
                for path in (
                    urlparse(request.get("url", "")).path
                    for request in self._matching_requests_to(
                        driver, GENERATIONS_PATH, method="GET"
                    )
                )
                if _is_status_poll_path(path)
            }

        assert polled_paths, (
            f"expected the client to be polling GET {GENERATIONS_PATH}/<id> while the generation "
            "runs, but no status request was issued — the generating state is not being watched "
            "and would never resolve (collection loads of "
            f"{GENERATIONS_PATH} do not count: they carry no run id)"
        )
        assert len(polled_paths) == 1, (
            f"expected every status check to poll the one run that was just started, got "
            f"{len(polled_paths)} distinct paths {sorted(polled_paths)}"
        )

        polled_path = polled_paths.pop()
        generation_id = polled_path.rsplit("/", 1)[-1]

        # The id itself is the one genuinely opaque value here: it is minted by the backend and
        # returned in the create POST's RESPONSE body, which `Network.requestWillBeSent` does not
        # carry — so there is no way to capture it for an equality check from the performance log.
        # Its FORMAT is not opaque, and pinning it is what rejects `/api/v1/generations/undefined`,
        # the shape a broken id hand-off actually produces.
        assert is_uuid(generation_id), (
            f"expected the polled run id to be a UUID, got '{generation_id}' in "
            f"'{polled_path}' — the generation id was not threaded into the status poll"
        )
