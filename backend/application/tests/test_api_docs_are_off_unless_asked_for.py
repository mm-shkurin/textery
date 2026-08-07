"""`/docs`, `/redoc` and `/openapi.json` are published only when asked for.

`FastAPI()` serves all three unless told otherwise, and this app never told it
otherwise. Through the frontend origin that is invisible -- nginx proxies only
`/api/` -- but `infra/docker-compose.yml` publishes the backend's own port on the
host, and on that port every route, schema and error code was readable by anyone
who reached it.
"""

import pytest
from api_docs import API_DOCS_ENABLED_ENV_VAR, api_docs_enabled, docs_urls


@pytest.fixture(autouse=True)
def _no_inherited_setting(monkeypatch):
    """Start every case from "the variable is not set".

    Without this the suite's answer depends on the developer's own environment:
    a shell with API_DOCS_ENABLED=1 exported would turn the fail-closed cases
    green while proving the opposite of what they claim.
    """
    monkeypatch.delenv(API_DOCS_ENABLED_ENV_VAR, raising=False)


class TestDocumentationIsOffByDefault:
    def test_should_publish_nothing_when_the_variable_is_absent(self):
        assert docs_urls() == (None, None, None), (
            "an unconfigured process must publish no documentation: the default is "
            "what applies in the environments where nobody thought about it"
        )

    def test_should_clear_the_schema_and_not_only_the_viewer(self):
        """`openapi_url` matters more than `docs_url`, and is the one easily forgotten.

        Clearing the viewer while leaving the schema served hides the rendering
        and publishes everything it was rendering -- it reads as "documentation
        disabled" while disabling nothing that matters.
        """
        assert docs_urls().openapi_url is None


class TestDocumentationIsOnWhenAskedFor:
    @pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on", " true "])
    def test_should_publish_all_three_for_an_affirmative_value(self, value, monkeypatch):
        monkeypatch.setenv(API_DOCS_ENABLED_ENV_VAR, value)

        assert docs_urls() == ("/docs", "/redoc", "/openapi.json")

    def test_should_serve_the_paths_fastapi_uses_by_default(self):
        """The enabled paths are FastAPI's own, so turning this on changes nothing else.

        A different path would silently break every bookmark, README line and
        client generator that already points at `/docs`.
        """
        import os

        os.environ[API_DOCS_ENABLED_ENV_VAR] = "1"
        try:
            assert docs_urls().docs_url == "/docs"
            assert docs_urls().redoc_url == "/redoc"
        finally:
            del os.environ[API_DOCS_ENABLED_ENV_VAR]


class TestUnrecognisedValuesFailClosed:
    @pytest.mark.parametrize("value", ["0", "false", "no", "off", "", "  ", "maybe", "2"])
    def test_should_treat_anything_unrecognised_as_off(self, value, monkeypatch):
        """`false` and `0` are what someone writes meaning off.

        Under a truthiness test both are non-empty strings and would turn
        documentation ON -- the exact opposite of the intent, with nothing
        reporting it. This is the assertion that makes the explicit allowlist in
        `api_docs.py` load-bearing rather than stylistic.
        """
        monkeypatch.setenv(API_DOCS_ENABLED_ENV_VAR, value)

        assert api_docs_enabled() is False, (
            f"{value!r} must not enable documentation; anything not on the "
            f"affirmative list is off, because this is the fail-closed side"
        )
