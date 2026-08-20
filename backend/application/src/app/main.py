import os
import sys

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_APPLICATION_SRC = os.path.dirname(_APP_DIR)
_APPLICATION_DIR = os.path.dirname(_APPLICATION_SRC)
_BACKEND_DIR = os.path.dirname(_APPLICATION_DIR)
_REST_SRC = os.path.join(_BACKEND_DIR, "adapters", "rest", "src")
_DOMAIN_SRC = os.path.join(_BACKEND_DIR, "domain", "src")
_USECASE_SRC = os.path.join(_BACKEND_DIR, "usecase", "src")
_DB_SRC = os.path.join(_BACKEND_DIR, "adapters", "db", "src")
_PROVIDER_SRC = os.path.join(_BACKEND_DIR, "adapters", "generation_provider", "src")
_OAUTH_PROVIDER_SRC = os.path.join(_BACKEND_DIR, "adapters", "oauth_provider", "src")
_SECURITY_SRC = os.path.join(_BACKEND_DIR, "adapters", "security", "src")
_RENDERING_SRC = os.path.join(_BACKEND_DIR, "adapters", "rendering", "src")

sys.path.insert(0, _APP_DIR)
sys.path.insert(0, _REST_SRC)
sys.path.insert(0, _DOMAIN_SRC)
sys.path.insert(0, _USECASE_SRC)
sys.path.insert(0, _DB_SRC)
sys.path.insert(0, _PROVIDER_SRC)
sys.path.insert(0, _OAUTH_PROVIDER_SRC)
sys.path.insert(0, _SECURITY_SRC)
# The export wiring lazy-imports WeasyPrintPdfRenderer from here at request time;
# without this root a real export 500s with ModuleNotFoundError: 'rendering'.
sys.path.insert(0, _RENDERING_SRC)

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator

from api_docs import docs_urls
from dependency_wiring import install_dependency_overrides
from fastapi import FastAPI
from middleware.no_store import NoStoreMiddleware

from container import provider, run_stale_generation_sweep
from error_handling.exception_handlers import (
    conflict_exception_handler,
    not_found_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from logging_config import configure_logging
from router.auth.auth_router import router as auth_router
from router.auth.avatar_router import router as avatar_router
from router.auth.deletion_router import router as deletion_router
from router.auth.oauth_router import router as oauth_router
from router.auth.profile_router import router as profile_router
from router.document.document_deletion_router import router as document_deletion_router
from router.document.document_router import router as document_router
from router.generation.generation_router import router as generation_router
from router.health.health_router import router as health_router
from router.project.project_router import router as project_router
from shared.exceptions import ConflictException, NotFoundException, ValidationException

SWEEP_INTERVAL_SECONDS = 60

# Before the first logger is taken, and before `app` exists: handlers installed
# after a record is emitted do not retroactively deliver it, and the composition
# root's own import-time failures (an unset DATABASE_URL, a short JWT_SECRET) are
# exactly the ones worth having formatted.
configure_logging()

logger = logging.getLogger(__name__)


async def _sweep_loop() -> None:
    while True:
        await asyncio.sleep(SWEEP_INTERVAL_SECONDS)
        try:
            await run_stale_generation_sweep()
        except Exception:
            logger.exception("stale generation sweep failed")


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    sweep_task = asyncio.create_task(_sweep_loop())
    try:
        yield
    finally:
        sweep_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await sweep_task
        # The provider holds a pooled HTTP client for the life of the process, so
        # something has to hand it back. Cancelled AFTER the sweep task, not
        # before: the sweep drives generations through this same provider, and
        # closing the pool out from under an in-flight request would turn an
        # orderly shutdown into a logged failure.
        await provider.aclose()


# Off unless API_DOCS_ENABLED says so; api_docs.py has the why.
_docs = docs_urls()
app = FastAPI(
    lifespan=lifespan,
    docs_url=_docs.docs_url,
    redoc_url=_docs.redoc_url,
    openapi_url=_docs.openapi_url,
)
app.include_router(generation_router)
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(avatar_router)
app.include_router(deletion_router)
app.include_router(oauth_router)
app.include_router(document_router)
# After document_router: both carry the /api/v1/documents prefix, and the literal
# routes there must stay above any parameterised one registered later.
app.include_router(document_deletion_router)
app.include_router(health_router)
app.include_router(project_router)
# The three narrow handlers are suppressed below because Starlette types the
# second argument as taking `Exception`, while it dispatches on the class given
# in the first argument, so a handler narrowed to the class it is registered for
# is the intended usage and cannot be called with anything else. Typing that
# relationship needs a dependent signature Starlette does not express. Suppressed
# per line, with the code named, rather than by loosening the handlers to
# `Exception` -- that would erase a real guarantee to satisfy a stub.
app.add_exception_handler(ValidationException, validation_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(NotFoundException, not_found_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(ConflictException, conflict_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, unhandled_exception_handler)
# Stamps Cache-Control: no-store on every response the profile routes produce --
# the 200 and, because it wraps the router rather than living inside a route body,
# the 401 the auth dependency raises before any body runs. The 500 is stamped by
# unhandled_exception_handler instead: Starlette builds ServerErrorMiddleware
# outside the user middleware stack, so that one response never passes through
# here. Both read the same is_profile_path predicate.
app.add_middleware(NoStoreMiddleware)

# Every wiring of a router's placeholder dependency to its composition-root
# factory lives in dependency_wiring: it is one line per usecase and grows with
# every endpoint, which is what pushed this file past the 200-line cap.
install_dependency_overrides(app)
