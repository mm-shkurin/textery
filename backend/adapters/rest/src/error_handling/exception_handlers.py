from fastapi import Request
from fastapi.responses import JSONResponse

from shared.exceptions import ValidationException


async def validation_exception_handler(request: Request, exc: ValidationException) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "internal server error"})
