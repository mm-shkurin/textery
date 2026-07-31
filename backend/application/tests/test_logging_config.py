import logging

import pytest

from logging_config import (
    DEFAULT_LOG_LEVEL,
    LOG_LEVEL_ENV_VAR,
    configure_logging,
    resolve_log_level,
)


class TestResolveLogLevel:
    def test_should_default_to_info_when_unset(self, monkeypatch):
        """INFO, not WARNING. At WARNING the two exception handlers that record a
        refused 404/409 go silent, which is the state this module was written to
        end.
        """
        monkeypatch.delenv(LOG_LEVEL_ENV_VAR, raising=False)

        assert resolve_log_level() == "INFO"
        assert DEFAULT_LOG_LEVEL == "INFO"

    @pytest.mark.parametrize("configured", ["DEBUG", "debug", "Warning", "ERROR"])
    def test_should_accept_a_configured_level_case_insensitively(self, monkeypatch, configured):
        monkeypatch.setenv(LOG_LEVEL_ENV_VAR, configured)

        assert resolve_log_level() == configured.upper()

    def test_should_fall_back_rather_than_raise_on_a_misspelled_level(self, monkeypatch):
        """A typo in an observability knob must not be a boot failure.

        `DATABASE_URL` and `JWT_SECRET` refuse to start because a wrong value there
        is unserviceable. A wrong level has a safe answer, and refusing to boot
        over it would turn a typo into an outage.
        """
        monkeypatch.setenv(LOG_LEVEL_ENV_VAR, "VERBOSE")

        assert resolve_log_level() == DEFAULT_LOG_LEVEL


class TestConfigureLogging:
    @pytest.fixture(autouse=True)
    def restore_root_logger(self):
        root = logging.getLogger()
        saved_handlers, saved_level = root.handlers[:], root.level
        yield
        root.handlers[:] = saved_handlers
        root.setLevel(saved_level)

    def test_should_install_a_handler_on_the_root_logger(self, monkeypatch):
        monkeypatch.delenv(LOG_LEVEL_ENV_VAR, raising=False)

        configure_logging()

        assert logging.getLogger().handlers != []

    def test_should_set_the_root_level_from_the_environment(self, monkeypatch):
        monkeypatch.setenv(LOG_LEVEL_ENV_VAR, "DEBUG")

        configure_logging()

        assert logging.getLogger().level == logging.DEBUG

    def test_should_deliver_an_info_record_from_a_module_logger(self, monkeypatch, capsys):
        """The regression this module exists for.

        Module loggers are never configured individually -- they propagate to root.
        An INFO record from one of them reaching the stream is the proof that the
        404/409 lines in the exception handlers are no longer discarded.
        """
        monkeypatch.delenv(LOG_LEVEL_ENV_VAR, raising=False)
        configure_logging()

        logging.getLogger("usecase.somewhere").info("a refused request")

        assert "a refused request" in capsys.readouterr().err

    def test_should_format_records_with_level_and_logger_name(self, monkeypatch, capsys):
        """`logging.lastResort` emits the bare message. A traceback with no level,
        no timestamp and no logger name cannot be tied to a request, or even to
        this application rather than a library.
        """
        monkeypatch.delenv(LOG_LEVEL_ENV_VAR, raising=False)
        configure_logging()

        logging.getLogger("usecase.somewhere").warning("a warning")

        written = capsys.readouterr().err
        assert "WARNING" in written
        assert "usecase.somewhere" in written

    def test_should_leave_uvicorns_own_loggers_alive(self, monkeypatch):
        """`disable_existing_loggers` defaults to True in dictConfig, which would
        switch off `uvicorn.error` and `uvicorn.access` -- both already built by
        the time this runs -- and trade the application's silence for the server's.
        """
        monkeypatch.delenv(LOG_LEVEL_ENV_VAR, raising=False)
        uvicorn_logger = logging.getLogger("uvicorn.access")

        configure_logging()

        assert uvicorn_logger.disabled is False
