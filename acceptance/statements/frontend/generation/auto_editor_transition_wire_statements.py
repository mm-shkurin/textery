"""The wire half of story 18, scenario 2.1 — what the auto-transition did to the backend.

Split from `auto_editor_transition_statements.py` at the 200-line cap, the same way
`auto_editor_transition_expectations.py` was: that file holds the DOM half (the editor arrived,
by itself, loaded, editable), this one holds the network half.

The split is not only mechanical. Every DOM assertion in this scenario is an ABSENCE or a
PRESENCE on screen, and the two defects that hurt most here are invisible on screen by
construction:

  * the poll loop outliving its own result — hiding the generating surface and calling
    `stopPolling()` are independent lines in `useGeneration.ts`, so a green implementation that
    switches to the editor branch and forgets the teardown passes every absence check while
    `POLL_INTERVAL_MS = 5000` hammers the backend for as long as the tab stays open;
  * a conversion driven off a live poll tick — one duplicate document per tick, and React
    collapses the repeated editor mount, so the user sees one editor and finds four to nine
    identical documents in their list later.

Neither leaves a mark in the DOM. They leave marks on the wire, and this is where those are read.
"""

import time
from urllib.parse import urlparse

from selenium.webdriver.remote.webdriver import WebDriver

from statements.frontend.generation.generate_flow_statements import IDEMPOTENCY_KEY_HEADER
from statements.frontend.generation.generation_flow_actions import (
    GENERATIONS_PATH,
    is_status_poll_path,
)
from statements.uuid_format import is_uuid

# The only NEW endpoint story 18 defines (`endpoints.md`): the client converts a completed
# generation into an editable Document and opens the editor on the result.
CONVERSION_PATH = "/api/v1/documents/from-generation"

# How long to hold the wire quiet before declaring the poll loop dead. It MUST exceed
# `POLL_INTERVAL_MS` (5000, useGeneration.ts) or a leaked interval could simply not have ticked
# yet inside the observation window and the absence check would pass on the very defect it
# exists to catch. Two seconds of margin over one full interval, so a live loop is guaranteed at
# least one tick to betray itself with.
POLL_QUIET_SECONDS = 7


class AutoEditorTransitionWireMixin:
    """Assertions about the requests the auto-transition made, mixed into a BaseFrontendStatements."""

    def assert_the_conversion_created_exactly_one_document(self, driver: WebDriver) -> None:
        """One completed generation became ONE document, and it was THIS generation.

        Three separate claims, all read from ONE drain of the performance log, because
        `driver.get_log` empties the buffer: a second helper call would be handed an already
        emptied log and would report zero conversions for a flow that made several. That is
        why this uses `_drain_requests` + `_requests_matching` rather than two
        `_matching_requests_to` calls — this lane has been bitten by the drain before.

        (1) A conversion happened at all. Without it the editor could have been reached by
        mounting an empty editor over the finished text, which every DOM assertion here except
        the content equality would accept.

        (2) Exactly one document was created. Counted over DISTINCT `Idempotency-Key`s rather
        than raw requests, the same measure scenario 1.1 uses for the create POST and for the
        same reason: `authorizedRequest` replays a request VERBATIM on a 401, keeping the key
        the client minted once, and the backend collapses that pair onto one document. Counting
        requests would report a correct 401 replay as double-billing. A conversion fired off
        each poll tick mints a NEW key per tick, so it fails here — which is the incident this
        assertion exists for.

        (3) The conversion carried the run that was actually polled. The status polls are in
        the same drain, so the id can be compared rather than merely shape-checked; a
        format-only check would accept a conversion of some other (or stale) generation, which
        hands the user a document containing somebody else's text.
        """
        requests = self._drain_requests(driver)
        conversions = self._requests_matching(requests, CONVERSION_PATH, method="POST")

        assert conversions, (
            f"expected the completed generation to be converted via POST {CONVERSION_PATH} so "
            "the editor has a document to open, but no such request was made — the editor was "
            "reached without converting anything"
        )

        keys = [self._request_header(request, IDEMPOTENCY_KEY_HEADER) for request in conversions]
        # The key's VALUE is opaque (minted client-side, never surfaced), but its FORMAT is not,
        # and the distinct-key count below only measures "how many documents were created" if
        # every key is a real minted UUID: a "" or a constant placeholder would pass a presence
        # check and silently collapse N genuine conversions into one.
        assert all(is_uuid(key) for key in keys), (
            f"expected every POST {CONVERSION_PATH} to carry a UUID {IDEMPOTENCY_KEY_HEADER} so a "
            f"401 replay collapses server-side, got keys {keys}"
        )
        distinct_keys = set(keys)
        assert len(distinct_keys) == 1, (
            f"expected the completed generation to be converted into exactly ONE document (one "
            f"distinct {IDEMPOTENCY_KEY_HEADER}), got {len(distinct_keys)} across "
            f"{len(conversions)} POST {CONVERSION_PATH} request(s) with keys {keys} — the "
            "conversion is firing more than once (a poll tick driving it would mint one key and "
            "one duplicate document per tick, all invisible on screen)"
        )

        polled_ids = self._polled_run_ids(requests)
        assert len(polled_ids) == 1, (
            f"expected the run just started to be the only one polled, got {sorted(polled_ids)} — "
            f"cannot say which generation POST {CONVERSION_PATH} should have carried"
        )
        expected_generation_id = polled_ids.pop()
        body = self._request_body(conversions[0], f"POST {CONVERSION_PATH}")
        assert body == {"generation_id": expected_generation_id}, (
            f"expected POST {CONVERSION_PATH} to convert the generation this run polled "
            f"({expected_generation_id}), got body {body}"
        )

    def assert_the_poll_loop_stopped(self, driver: WebDriver) -> None:
        """The run was torn down, not merely hidden behind the editor.

        `assert_the_read_only_result_was_replaced` rules out a VISIBLE `generation-generating`
        surface, and that is all it can do: hiding the surface and calling `stopPolling()` are
        independent lines. This is the assertion that actually catches the leak the DOM cannot
        show — and the reason the other method's docstring no longer claims to.

        The window is opened by the preceding conversion assertion's drain (the log is empty
        after it) and closed by the drain below, with a deliberate quiet period in between that
        is longer than one full poll interval. So this observes a window in which a live
        interval MUST have ticked: an empty window is evidence, not merely an absence of
        evidence.

        Deliberately unbounded rather than "bounded to N": once the editor holds the text there
        is nothing left for the client to ask about, so the honest bound is zero. A green
        implementation that needs one more in-flight poll to settle should make this test say
        so explicitly, not hide inside a tolerance.
        """
        time.sleep(POLL_QUIET_SECONDS)
        polls = self._polled_run_ids(self._drain_requests(driver))

        assert not polls, (
            f"expected the status poll to stop once the editor opened, but the client kept "
            f"polling {sorted(polls)} for a further {POLL_QUIET_SECONDS}s — the poll loop "
            "outlived its own result and will hit the backend every 5s for as long as the tab "
            "is open, and any conversion driven off those ticks duplicates the document"
        )

    def _polled_run_ids(self, requests: list[dict]) -> set[str]:
        """The distinct run ids of the status polls in an already-drained batch.

        Takes a batch rather than a driver on purpose: both callers need this alongside another
        filter over the SAME drain, and a helper that drained for itself would eat the other's
        evidence.
        """
        paths = {
            urlparse(request.get("url", "")).path
            for request in self._requests_matching(requests, GENERATIONS_PATH, method="GET")
        }
        return {path.rsplit("/", 1)[-1] for path in paths if is_status_poll_path(path)}
