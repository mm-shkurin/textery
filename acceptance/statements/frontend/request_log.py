"""Reading the browser's CDP performance log — what the page actually put on the wire.

Split out of `base_frontend_statements.py` at the 200-line cap. `BaseFrontendStatements` mixes
this in, so every Statements class keeps reaching these under the same names as before.

Requires the webdriver fixture to enable `goog:loggingPrefs: {"performance": "ALL"}`.
"""

import json
import time

from selenium.webdriver.remote.webdriver import WebDriver

REQUEST_LOG_SETTLE_SECONDS = 1


class RequestLogMixin:
    """Drain, filter, and inspect `Network.requestWillBeSent` events."""

    def _drain_requests(self, driver: WebDriver) -> list[dict]:
        """Every CDP `request` object logged since the last drain, unfiltered.

        Sleeps briefly first since CDP log delivery is asynchronous relative to the triggering
        gesture.

        WARNING: `driver.get_log` DRAINS the performance buffer — a second call returns only
        events logged since the first. This method exists so a caller that needs to assert about
        TWO DIFFERENT request shapes (say a POST to one path and the GETs to another) can take
        both from ONE drain: calling `_matching_requests_to` twice would hand the second call an
        already-emptied buffer and report zero for a flow that made several.
        """
        time.sleep(REQUEST_LOG_SETTLE_SECONDS)

        requests = []
        for entry in driver.get_log("performance"):
            message = json.loads(entry["message"])["message"]
            if message.get("method") != "Network.requestWillBeSent":
                continue
            requests.append(message.get("params", {}).get("request", {}))
        return requests

    @staticmethod
    def _requests_matching(
        requests: list[dict], path_substring: str, method: str = "POST"
    ) -> list[dict]:
        """Filters an already-drained batch by URL substring and HTTP method.

        Pure — takes no driver and drains nothing — so it can be applied repeatedly to one
        `_drain_requests` result without the buffer hazard above.
        """
        return [
            request
            for request in requests
            if path_substring in request.get("url", "") and request.get("method") == method
        ]

    def _matching_requests_to(
        self, driver: WebDriver, path_substring: str, method: str = "POST"
    ) -> list[dict]:
        """The requests whose URL contains `path_substring` and whose method matches `method`
        (default "POST" — excludes CORS preflight OPTIONS requests to the same URL).

        WARNING: this DRAINS the performance buffer (see `_drain_requests`). Callers that need
        both a count and the payloads must take them from ONE call to this method, never from
        two helpers; callers that need two different request shapes must use `_drain_requests` +
        `_requests_matching` instead.
        """
        return self._requests_matching(self._drain_requests(driver), path_substring, method)

    def _count_requests_to(self, driver: WebDriver, path_substring: str, method: str = "POST") -> int:
        """Number of matching requests. See `_matching_requests_to` for the drain warning."""
        return len(self._matching_requests_to(driver, path_substring, method))

    @staticmethod
    def _request_header(request: dict, name: str) -> str | None:
        """Case-insensitive header lookup on one CDP `request` object.

        `Network.requestWillBeSent` reports headers exactly as they went on the wire, and header
        names are case-insensitive there, so a literal dict lookup would silently miss a
        differently-cased key and report the header as absent.
        """
        wanted = name.lower()
        for key, value in (request.get("headers") or {}).items():
            if key.lower() == wanted:
                return value
        return None

    @staticmethod
    def _request_body(request: dict, label: str) -> dict:
        """Parses one CDP request's JSON post body, failing loudly if it carried none."""
        post_data = request.get("postData")
        assert post_data is not None, f"expected {label} to carry a JSON body, got none"
        return json.loads(post_data)
