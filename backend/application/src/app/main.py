import os
import sys

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_APPLICATION_SRC = os.path.dirname(_APP_DIR)
_APPLICATION_DIR = os.path.dirname(_APPLICATION_SRC)
_BACKEND_DIR = os.path.dirname(_APPLICATION_DIR)
_REST_SRC = os.path.join(_BACKEND_DIR, "adapters", "rest", "src")
_DOMAIN_SRC = os.path.join(_BACKEND_DIR, "domain", "src")
_USECASE_SRC = os.path.join(_BACKEND_DIR, "usecase", "src")

sys.path.insert(0, _REST_SRC)
sys.path.insert(0, _DOMAIN_SRC)
sys.path.insert(0, _USECASE_SRC)

from fastapi import FastAPI

from error_handling.exception_handlers import unhandled_exception_handler, validation_exception_handler
from router.generation.generation_router import router as generation_router
from shared.exceptions import ValidationException

app = FastAPI()
app.include_router(generation_router)
app.add_exception_handler(ValidationException, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)
