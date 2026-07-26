"""CDP-based network throttling shared by in-flight-lock Selenium scenarios.

Chrome DevTools Protocol lets a test hold every response open for a fixed latency, so a
first request stays in flight long enough for a second user action to land inside the
in-flight window. Two scenarios exercise the identical control — the manual-editor save
queue (4.2) and the export in-flight lock (2.1) — so the mechanism (and its latency
constant, which both must keep in sync) lives here rather than duplicated per file.
"""


# Latency (ms) held on every response while throttled — large enough that the first
# request stays open across a follow-up click, so the in-flight lock is genuinely under
# test. Both throttled scenarios share this single source of truth.
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
