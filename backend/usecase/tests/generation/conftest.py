"""Fixtures for the generation usecases."""

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
