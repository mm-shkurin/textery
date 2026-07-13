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

sys.path.insert(0, _APP_DIR)
sys.path.insert(0, _REST_SRC)
sys.path.insert(0, _DOMAIN_SRC)
sys.path.insert(0, _USECASE_SRC)
sys.path.insert(0, _DB_SRC)
sys.path.insert(0, _PROVIDER_SRC)

import asyncio
import contextlib
import logging

from fastapi import FastAPI

from container import (
    create_generate_document,
    create_get_generation,
    create_register_user,
    create_request_generation,
    run_stale_generation_sweep,
)
from error_handling.exception_handlers import unhandled_exception_handler, validation_exception_handler
from router.auth.auth_router import get_register_user_usecase
from router.auth.auth_router import router as auth_router
from router.generation.generation_router import (
    get_generate_document_usecase,
    get_get_generation_usecase,
    get_request_generation_usecase,
)
from router.generation.generation_router import router as generation_router
from shared.exceptions import ValidationException

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
app.add_exception_handler(ValidationException, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.dependency_overrides[get_request_generation_usecase] = create_request_generation
app.dependency_overrides[get_get_generation_usecase] = create_get_generation
app.dependency_overrides[get_generate_document_usecase] = create_generate_document
app.dependency_overrides[get_register_user_usecase] = create_register_user
