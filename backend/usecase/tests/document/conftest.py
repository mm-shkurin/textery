"""Fixtures for the document usecases."""

import pytest

from statements.document_scope_guard_statements import DocumentScopeGuardStatements


@pytest.fixture
def document_scope_guard_statements():
    return DocumentScopeGuardStatements()
