"""What the lookup client answers, and what it puts on the wire.

`04_Infrastructure_Tests.md` §2 says this client never raises, is asked once, is
bounded, and never puts its token in a log. Until now every one of those was a
docstring: the adapter had no tests at all, while `pyproject.toml` counted it in
`[tool.coverage.run] source`, so its lines dragged the project number down and
none of its behaviour was checked.

Configuration and lifecycle are in `test_http_geolocation_configuration.py`; the
shared no-socket client is in `conftest.py`.
"""

import httpx
import pytest


def _refusing(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("connection refused", request=request)


class TestTheCountryItReads:
    async def test_reads_the_two_letter_code(self, answering, ok):
        client = answering(ok({"countryCode": "RU"}))

        assert await client.country_of("203.0.113.7") == "RU"

    async def test_falls_back_to_the_long_key_when_the_short_one_is_absent(self, answering, ok):
        client = answering(ok({"country": "de"}))

        assert await client.country_of("203.0.113.7") == "DE"

    async def test_upper_cases_the_answer(self, answering, ok):
        """One provider answers `ru` and another `RU`; Story 15 groups by ONE value."""
        client = answering(ok({"countryCode": "ru"}))

        assert await client.country_of("203.0.113.7") == "RU"

    @pytest.mark.parametrize(
        "body",
        [
            {"countryCode": ""},
            {"countryCode": "   "},
            {"countryCode": 7},
            {"unrelated": "RU"},
            ["RU"],
            "RU",
            None,
        ],
        ids=["empty", "blank", "not-a-string", "wrong-key", "list", "scalar", "null"],
    )
    async def test_answers_none_for_a_body_that_carries_no_country(self, body, answering, ok):
        client = answering(ok(body))

        assert await client.country_of("203.0.113.7") is None


class TestItNeverRaises:
    """§2.1 — a dependency that is down leaves the column NULL, not the registration broken."""

    async def test_a_refused_connection_answers_none(self, answering):
        client = answering(_refusing)

        assert await client.country_of("203.0.113.7") is None

    async def test_a_timeout_answers_none(self, answering):
        def hang(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out", request=request)

        client = answering(hang)

        assert await client.country_of("203.0.113.7") is None

    @pytest.mark.parametrize("status", [400, 401, 429, 500, 503])
    async def test_an_error_status_answers_none(self, status, answering):
        def refused(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(status, json={"countryCode": "RU"})

        client = answering(refused)

        assert await client.country_of("203.0.113.7") is None

    async def test_a_body_that_is_not_json_answers_none(self, answering):
        def html(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="<html>nope</html>")

        client = answering(html)

        assert await client.country_of("203.0.113.7") is None


class TestItIsAskedOnce:
    """§1.3 — no retry loop: a retry multiplies the latency a registering user waits."""

    async def test_a_failure_produces_exactly_one_request(self, answering):
        client = answering(_refusing)

        await client.country_of("203.0.113.7")

        assert len(client.requests) == 1

    @pytest.mark.parametrize("absent", [None, ""], ids=["none", "empty"])
    async def test_no_address_costs_no_request_at_all(self, absent, answering, ok):
        client = answering(ok({"countryCode": "RU"}))

        assert await client.country_of(absent) is None
        assert client.requests == []


class TestWhatGoesOnTheWire:
    async def test_the_address_is_the_last_path_segment_under_a_normalised_base(
        self, answering, ok
    ):
        """The base URL is given with a trailing slash; the path must not double it."""
        client = answering(ok({"countryCode": "RU"}))

        await client.country_of("203.0.113.7")

        sent = client.requests[0]
        assert sent.url.path == "/203.0.113.7"
        assert sent.url.host == "lookup.local"

    async def test_the_token_travels_as_a_query_credential(self, answering, ok):
        client = answering(ok({"countryCode": "RU"}))

        await client.country_of("203.0.113.7")

        assert client.requests[0].url.params["token"] == "SECRET"


class TestTheTokenNeverReachesTheLog:
    """§5.6 — an httpx message renders the full URL, which carries the credential."""

    async def test_a_failure_logs_the_error_class_and_nothing_else(self, answering, caplog):
        def fail(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError(f"failed connecting to {request.url}", request=request)

        client = answering(fail)

        with caplog.at_level("WARNING"):
            await client.country_of("203.0.113.7")

        logged = caplog.text
        assert "ConnectError" in logged
        assert "SECRET" not in logged
        assert "lookup.local" not in logged
