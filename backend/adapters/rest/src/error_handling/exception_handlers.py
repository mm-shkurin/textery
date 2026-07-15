import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from shared.exceptions import ValidationException

logger = logging.getLogger(__name__)

_ERROR_CODE_STATUS_MAP = {
    "EMAIL_ALREADY_REGISTERED": 409,
}


async def validation_exception_handler(request: Request, exc: ValidationException) -> JSONResponse:
    status_code = _ERROR_CODE_STATUS_MAP.get(exc.error_code, 400)
    return JSONResponse(status_code=status_code, content={"error_code": exc.error_code, "message": exc.message})


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "internal server error"})
