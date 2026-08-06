import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from shared.exceptions import ConflictException, NotFoundException, ValidationException

logger = logging.getLogger(__name__)

# Explicit per-code mapping with a 400 default. An if/else chain here would make
# a silently-wrong status the easy mistake; a dict makes each choice visible.
_ERROR_CODE_STATUS_MAP = {
    "EMAIL_ALREADY_REGISTERED": 409,
    "ALREADY_VERIFIED": 409,
    "RESEND_COOLDOWN_ACTIVE": 429,
    "OAUTH_RATE_LIMITED": 429,
    "INVALID_CREDENTIALS": 401,
    "INVALID_REFRESH_TOKEN": 401,
    "UNVERIFIED": 403,
    "UNAUTHORIZED": 401,
    # projects_list.yaml declares 401 for an owner that cannot be resolved, and
    # ListProjects.execute refuses one with this code. Without the entry the
    # default answers 400, telling the client its request was malformed.
    "UNAUTHENTICATED": 401,
    "INVALID_DOCUMENT_TYPE": 422,
    "INVALID_IDEMPOTENCY_KEY": 422,
    "INVALID_VERSION": 422,
    "INVALID_FORMAT": 422,
    # Generation-to-document conversion (documents_from_generation.yaml). The two
    # 409s are refusals to convert, NOT the save path's version conflict, so they
    # carry their own codes: routing them through ConflictException would answer
    # with "The document was modified by another save", which is untrue and
    # unactionable for a client that has not saved anything yet.
    "GENERATION_NOT_COMPLETED": 409,
    "IDEMPOTENCY_KEY_REUSED": 409,
    # «Повторить» (generations_retry.yaml). NOT_RETRYABLE is a refusal to start
    # work on a row in the wrong state; RETRY_LIMIT_REACHED is the per-source
    # ceiling, which is a rate limit rather than a malformed request and so
    # answers 429 like the other shed paths.
    "NOT_RETRYABLE": 409,
    "RETRY_LIMIT_REACHED": 429,
    "CONVERTED_CONTENT_TOO_LONG": 422,
    # CONTENT_TOO_LONG is absent deliberately: documents_save.yaml specifies 400 for
    # it, which is the default.
}

# Fixed, client-safe bodies. The exceptions are raised with internal detail --
# NotFoundException(f"document {id} not found") -- and echoing str(exc) would put
# an internal id shape in the response, which Security 5.1 names explicitly as a
# leak. The detail is logged instead.
NOT_FOUND_MESSAGE = "The requested resource was not found."
CONFLICT_MESSAGE = "The document was modified by another save. Refetch and retry."
INTERNAL_ERROR_MESSAGE = "An unexpected error occurred. Please try again."


async def validation_exception_handler(request: Request, exc: ValidationException) -> JSONResponse:
    status_code = _ERROR_CODE_STATUS_MAP.get(exc.error_code, 400)
    return JSONResponse(
        status_code=status_code, content={"error_code": exc.error_code, "message": exc.message}
    )


async def not_found_exception_handler(request: Request, exc: NotFoundException) -> JSONResponse:
    """404 in the canonical shape.

    Before this, NotFoundException had no handler and fell through to the 500
    handler, so every missing resource was an internal server error.
    """
    logger.info("not found on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=404, content={"error_code": "NOT_FOUND", "message": NOT_FOUND_MESSAGE}
    )


async def conflict_exception_handler(request: Request, exc: ConflictException) -> JSONResponse:
    logger.info("conflict on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=409, content={"error_code": "VERSION_CONFLICT", "message": CONFLICT_MESSAGE}
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """500 in the canonical {error_code, message} shape, like every handler here.

    The message is fixed and generic for the same reason the 404's is: this
    catches exceptions nobody predicted, so str(exc) is an arbitrary internal
    string -- a driver error naming a table, a stack-shaped repr -- and echoing it
    hands that to the client. The detail goes to the log with its traceback.
    """
    logger.error(
        "unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=exc
    )
    return JSONResponse(
        status_code=500,
        content={"error_code": "INTERNAL_ERROR", "message": INTERNAL_ERROR_MESSAGE},
    )
