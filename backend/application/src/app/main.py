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

sys.path.insert(0, _APP_DIR)
sys.path.insert(0, _REST_SRC)
sys.path.insert(0, _DOMAIN_SRC)
sys.path.insert(0, _USECASE_SRC)
sys.path.insert(0, _DB_SRC)
sys.path.insert(0, _PROVIDER_SRC)
sys.path.insert(0, _OAUTH_PROVIDER_SRC)
sys.path.insert(0, _SECURITY_SRC)

import asyncio
import contextlib
import logging

from fastapi import FastAPI

from container import (
    create_complete_oauth_callback,
    create_create_document,
    create_exchange_handoff_code,
    create_frontend_callback_url,
    create_generate_document,
    create_get_document,
    create_get_generation,
    create_list_documents,
    create_list_generations,
    create_login_user,
    create_refresh_access_token,
    create_register_user,
    create_request_generation,
    create_resend_code,
    create_save_document,
    create_start_oauth,
    create_token_service,
    create_verify_account,
    run_stale_generation_sweep,
)
from error_handling.exception_handlers import (
    conflict_exception_handler,
    not_found_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
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
    get_create_document_usecase,
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
)
from router.generation.generation_router import router as generation_router
from security.current_owner import get_token_service
from shared.exceptions import ConflictException, NotFoundException, ValidationException

SWEEP_INTERVAL_SECONDS = 60

logger = logging.getLogger(__name__)


async def _sweep_loop() -> None:
    while True:
        await asyncio.sleep(SWEEP_INTERVAL_SECONDS)
        try:
            await run_stale_generation_sweep()
        except Exception:
            logger.exception("stale generation sweep failed")


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    sweep_task = asyncio.create_task(_sweep_loop())
    try:
        yield
    finally:
        sweep_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await sweep_task


app = FastAPI(lifespan=lifespan)
app.include_router(generation_router)
app.include_router(auth_router)
app.include_router(oauth_router)
app.include_router(document_router)
app.add_exception_handler(ValidationException, validation_exception_handler)
app.add_exception_handler(NotFoundException, not_found_exception_handler)
app.add_exception_handler(ConflictException, conflict_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.dependency_overrides[get_request_generation_usecase] = create_request_generation
app.dependency_overrides[get_get_generation_usecase] = create_get_generation
app.dependency_overrides[get_list_generations_usecase] = create_list_generations
app.dependency_overrides[get_generate_document_usecase] = create_generate_document
app.dependency_overrides[get_register_user_usecase] = create_register_user
app.dependency_overrides[get_verify_account_usecase] = create_verify_account
app.dependency_overrides[get_resend_code_usecase] = create_resend_code
app.dependency_overrides[get_login_user_usecase] = create_login_user
app.dependency_overrides[get_refresh_access_token_usecase] = create_refresh_access_token
app.dependency_overrides[get_create_document_usecase] = create_create_document
app.dependency_overrides[get_get_document_usecase] = create_get_document
app.dependency_overrides[get_list_documents_usecase] = create_list_documents
app.dependency_overrides[get_save_document_usecase] = create_save_document
app.dependency_overrides[get_token_service] = create_token_service
app.dependency_overrides[get_start_oauth_usecase] = create_start_oauth
app.dependency_overrides[get_complete_oauth_callback_usecase] = create_complete_oauth_callback
app.dependency_overrides[get_exchange_handoff_code_usecase] = create_exchange_handoff_code
app.dependency_overrides[get_frontend_callback_url] = create_frontend_callback_url
