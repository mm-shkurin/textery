import os
import sys

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_USECASE_DIR = os.path.dirname(_TESTS_DIR)
_BACKEND_DIR = os.path.dirname(_USECASE_DIR)
_DOMAIN_SRC = os.path.join(_BACKEND_DIR, "domain", "src")
_USECASE_SRC = os.path.join(_USECASE_DIR, "src")

sys.path.insert(0, _TESTS_DIR)
sys.path.insert(0, _DOMAIN_SRC)
sys.path.insert(0, _USECASE_SRC)

import pytest

from statements.generation_lifecycle_statements import GenerationLifecycleStatements
from statements.generation_statements import GenerationStatements
from statements.requeue_stale_generations_statements import RequeueStaleGenerationsStatements


@pytest.fixture
def generation_statements():
    return GenerationStatements()


@pytest.fixture
def generation_lifecycle_statements():
    return GenerationLifecycleStatements()


@pytest.fixture
def requeue_stale_generations_statements():
    return RequeueStaleGenerationsStatements()
