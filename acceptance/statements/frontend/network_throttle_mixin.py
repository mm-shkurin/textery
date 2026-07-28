"""CDP-based network throttling shared by in-flight-lock Selenium scenarios.

Chrome DevTools Protocol lets a test hold every response open for a fixed latency, so a
request stays in flight long enough for the test to observe or act inside that window. Three
scenarios exercise the identical control, so the mechanism (and its latency constant, which
they must keep in sync) lives here rather than duplicated per file:

- the manual-editor save queue (4.2) and the export in-flight lock (2.1), which need a SECOND
  user action to land while the first request is still open;
- the generating state (story 18, 1.2), which needs no second action — it holds the create
  POST open so the transient pending SURFACE stays observable, since the acceptance stack's
  fake provider otherwise answers faster than WebDriverWait polls.
"""


# Latency (ms) held on every response while throttled — large enough that the first
# request stays open across a follow-up click, so the in-flight lock is genuinely under
# test. All three throttled scenarios share this single source of truth.
#
# Story 18's 1.2 needs MORE from this value than 4.2/2.1 do: they need the window wide
# enough for one follow-up click, while 1.2 needs it wide enough to outlast a full DOM
# assertion pass. Lowering it for the in-flight-lock scenarios would reintroduce the
# millisecond-wide flake 1.2 exists to remove. `generating_state_statements` derives its
# poll-scan budget from this constant so the two cannot drift apart silently.
SLOW_LATENCY_MS = 2500


class NetworkThrottleMixin:
    """Adds `throttle_network` / `clear_network_throttle` to a Statements class.

    Generic over any Selenium `driver` exposing `execute_cdp_cmd`; carries no editor- or
    scenario-specific state, so any Statements class can mix it in.
    """

    def throttle_network(self, driver) -> None:
        driver.execute_cdp_cmd("Network.enable", {})
        driver.execute_cdp_cmd(
            "Network.emulateNetworkConditions",
            {
                "offline": False,
                "latency": SLOW_LATENCY_MS,
                "downloadThroughput": -1,
                "uploadThroughput": -1,
            },
        )

    def clear_network_throttle(self, driver) -> None:
        driver.execute_cdp_cmd(
            "Network.emulateNetworkConditions",
            {"offline": False, "latency": 0, "downloadThroughput": -1, "uploadThroughput": -1},
        )
