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

from fastapi import FastAPI

from container import (
    create_check_health,
    create_complete_oauth_callback,
    create_create_document,
    create_create_document_from_generation,
    create_exchange_handoff_code,
    create_export_document,
    create_frontend_callback_url,
    create_generate_document,
    create_get_document,
    create_get_generation,
    create_list_documents,
    create_list_generations,
    create_list_projects,
    create_login_user,
    create_refresh_access_token,
    create_register_user,
    create_request_generation,
    create_resend_code,
    create_retry_generation,
    create_save_document,
    create_start_oauth,
    create_token_service,
    create_verify_account,
    provider,
    run_stale_generation_sweep,
)
from error_handling.exception_handlers import (
    conflict_exception_handler,
    not_found_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from logging_config import configure_logging
from router.auth.auth_router import (
    get_login_user_usecase,
    get_refresh_access_token_usecase,
    get_register_user_usecase,
    get_resend_code_usecase,
    get_verify_account_usecase,
)
from router.auth.auth_router import router as auth_router
from router.auth.oauth_router import (
    get_complete_oauth_callback_usecase,
    get_exchange_handoff_code_usecase,
    get_frontend_callback_url,
    get_start_oauth_usecase,
)
from router.auth.oauth_router import router as oauth_router
from router.document.document_router import (
    get_create_document_from_generation_usecase,
    get_create_document_usecase,
    get_export_document_usecase,
    get_get_document_usecase,
    get_list_documents_usecase,
    get_save_document_usecase,
)
from router.document.document_router import router as document_router
from router.generation.generation_router import (
    get_generate_document_usecase,
    get_get_generation_usecase,
    get_list_generations_usecase,
    get_request_generation_usecase,
    get_retry_generation_usecase,
)
from router.generation.generation_router import router as generation_router
from router.health.health_router import get_check_health_usecase
from router.health.health_router import router as health_router
from router.project.project_router import get_list_projects_usecase
from router.project.project_router import router as project_router
from security.current_owner import get_token_service
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


app = FastAPI(lifespan=lifespan)
app.include_router(generation_router)
app.include_router(auth_router)
app.include_router(oauth_router)
app.include_router(document_router)
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

app.dependency_overrides[get_request_generation_usecase] = create_request_generation
app.dependency_overrides[get_get_generation_usecase] = create_get_generation
app.dependency_overrides[get_list_generations_usecase] = create_list_generations
app.dependency_overrides[get_retry_generation_usecase] = create_retry_generation
app.dependency_overrides[get_generate_document_usecase] = create_generate_document
app.dependency_overrides[get_register_user_usecase] = create_register_user
app.dependency_overrides[get_verify_account_usecase] = create_verify_account
app.dependency_overrides[get_resend_code_usecase] = create_resend_code
app.dependency_overrides[get_login_user_usecase] = create_login_user
app.dependency_overrides[get_refresh_access_token_usecase] = create_refresh_access_token
app.dependency_overrides[get_create_document_usecase] = create_create_document
app.dependency_overrides[get_get_document_usecase] = create_get_document
app.dependency_overrides[get_export_document_usecase] = create_export_document
app.dependency_overrides[get_create_document_from_generation_usecase] = (
    create_create_document_from_generation
)
app.dependency_overrides[get_list_documents_usecase] = create_list_documents
app.dependency_overrides[get_save_document_usecase] = create_save_document
app.dependency_overrides[get_token_service] = create_token_service
app.dependency_overrides[get_check_health_usecase] = create_check_health
app.dependency_overrides[get_list_projects_usecase] = create_list_projects
app.dependency_overrides[get_start_oauth_usecase] = create_start_oauth
app.dependency_overrides[get_complete_oauth_callback_usecase] = create_complete_oauth_callback
app.dependency_overrides[get_exchange_handoff_code_usecase] = create_exchange_handoff_code
app.dependency_overrides[get_frontend_callback_url] = create_frontend_callback_url
