import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from shared.exceptions import ValidationException

logger = logging.getLogger(__name__)


async def validation_exception_handler(request: Request, exc: ValidationException) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "internal server error"})
