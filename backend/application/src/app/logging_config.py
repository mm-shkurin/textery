"""Process-wide logging setup for the backend.

Twelve modules across `usecase` and `adapters` take a `logging.getLogger(__name__)`
and write carefully-levelled, lazily-formatted records. Nothing configured where
those records go, and the default is not "everything to stderr" -- it is the root
logger at WARNING with no handler at all. Two consequences, both silent:

  - every `logger.info` and `logger.debug` was DISCARDED. That is both 404 and 409
    in `error_handling/exception_handlers.py` -- the two lines that record which
    resource a client was refused -- and the stale-generation sweep's per-id trace.
  - `warning` and above still appeared, but through `logging.lastResort`, whose
    formatter is the bare message. The 500 handler's traceback arrived with no
    timestamp, no level, and no logger name, so nothing tied it to a request or
    even to this application rather than a library.

Running under uvicorn does not fix it. Uvicorn configures `uvicorn`, `uvicorn.error`
and `uvicorn.access` and deliberately leaves every other logger alone, so the
application's own tree is exactly as unconfigured as it is under plain `python`.
"""

import logging
import os
from logging.config import dictConfig

LOG_LEVEL_ENV_VAR = "LOG_LEVEL"
DEFAULT_LOG_LEVEL = "INFO"

# INFO rather than WARNING: at WARNING the two exception handlers that record a
# refused 404/409 go quiet, and those are the records that answer "did the client
# ever reach us" during an incident. The volume is one line per refused request,
# not per request.
_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


def resolve_log_level() -> str:
    """The configured level, falling back rather than refusing to start.

    Unlike `DATABASE_URL` and `JWT_SECRET`, which fail fast because a wrong value
    is unserviceable, a misspelled level has a safe answer: log at INFO. Refusing
    to boot over an observability knob would turn a typo into an outage.
    """
    requested = os.environ.get(LOG_LEVEL_ENV_VAR, DEFAULT_LOG_LEVEL).upper()
    if requested not in logging.getLevelNamesMapping():
        return DEFAULT_LOG_LEVEL
    return requested


def configure_logging() -> None:
    """Install one stderr handler on the root logger.

    stderr, not a file: the process runs in a container (`infra/docker/
    backend.Dockerfile`), where the collector reads the stream and a file inside
    the layer would be discarded with it.

    `disable_existing_loggers` is False, which is load-bearing here rather than
    boilerplate. This runs at import of `main`, by which point uvicorn has already
    built `uvicorn.error` and `uvicorn.access`; the default True would switch both
    off and trade the application's silence for the server's.

    Module loggers are left unconfigured on purpose -- they propagate to root, so
    one handler serves all twelve and a new module needs no entry here.
    """
    level = resolve_log_level()
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {"format": _FORMAT, "datefmt": _DATE_FORMAT},
            },
            "handlers": {
                "stderr": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stderr",
                    "formatter": "standard",
                },
            },
            "root": {"level": level, "handlers": ["stderr"]},
        }
    )
