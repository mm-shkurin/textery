"""Pytest fixtures for the story-10 editor-pages Statements DSLs.

Registered as a plugin via ``pytest_plugins`` in ``acceptance/conftest.py``, matching how
``manual_editor_fixtures.py`` is wired, so these resolve identically to conftest-defined
fixtures while keeping conftest under the 200-line file cap.
"""

import pytest

from statements.frontend.editor.editor_document_statements import EditorDocumentStatements
from statements.frontend.editor.pagination_measuring_statements import (
    PaginationMeasuringStatements,
)


@pytest.fixture
def editor_document_statements():
    return EditorDocumentStatements()


@pytest.fixture
def pagination_measuring_statements():
    return PaginationMeasuringStatements()
