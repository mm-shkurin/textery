"""Pytest fixtures for the manual-editor Statements DSLs.

Extracted from the root conftest to keep it under the 200-line file cap.
Registered as a plugin via ``pytest_plugins`` in ``acceptance/conftest.py``,
so these fixtures resolve identically to before across the acceptance suite.
"""

import pytest

from statements.frontend.generation.manual_editor_line_break_statements import (
    ManualEditorLineBreakStatements,
)
from statements.frontend.generation.manual_editor_aria_statements import (
    ManualEditorAriaStatements,
)
from statements.frontend.generation.manual_editor_beforeunload_statements import (
    ManualEditorBeforeUnloadStatements,
)
from statements.frontend.generation.manual_editor_caret_statements import (
    ManualEditorCaretStatements,
)
from statements.frontend.generation.manual_editor_placeholder_delete_statements import (
    ManualEditorPlaceholderDeleteStatements,
)
from statements.frontend.generation.manual_editor_popover_clip_statements import (
    ManualEditorPopoverClipStatements,
)
from statements.frontend.generation.manual_editor_save_payload_statements import (
    ManualEditorSavePayloadStatements,
)
from statements.frontend.generation.manual_editor_save_queue_statements import (
    ManualEditorSaveQueueStatements,
)
from statements.frontend.generation.manual_editor_export_control_statements import (
    ExportControlStatements,
)
from statements.frontend.generation.manual_editor_statements import ManualEditorStatements


@pytest.fixture
def manual_editor_statements():
    return ManualEditorStatements()


@pytest.fixture
def export_control_statements():
    return ExportControlStatements()


@pytest.fixture
def manual_editor_line_break_statements():
    return ManualEditorLineBreakStatements()


@pytest.fixture
def manual_editor_save_payload_statements():
    return ManualEditorSavePayloadStatements()


@pytest.fixture
def manual_editor_placeholder_delete_statements():
    return ManualEditorPlaceholderDeleteStatements()


@pytest.fixture
def manual_editor_aria_statements():
    return ManualEditorAriaStatements()


@pytest.fixture
def manual_editor_caret_statements():
    return ManualEditorCaretStatements()


@pytest.fixture
def manual_editor_save_queue_statements():
    return ManualEditorSaveQueueStatements()


@pytest.fixture
def manual_editor_popover_clip_statements():
    return ManualEditorPopoverClipStatements()


@pytest.fixture
def manual_editor_beforeunload_statements():
    return ManualEditorBeforeUnloadStatements()
