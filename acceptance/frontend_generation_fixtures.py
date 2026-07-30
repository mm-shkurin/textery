"""Frontend generation Statements fixtures (chat workspace, mode modal, manual editor).

Split out of conftest.py to keep that file under the 200-line cap. These names are
imported back into conftest (`from frontend_generation_fixtures import ...`), so
pytest discovers them exactly as if they were defined in conftest itself. This module
relies on conftest having already inserted the acceptance dir onto sys.path before it
imports us, which makes the `statements.*` imports below resolve.
"""

import pytest

from statements.frontend.generation.chat_workspace_statements import ChatWorkspaceStatements
from statements.frontend.generation.mode_modal_statements import ModeModalStatements
from statements.frontend.generation.manual_editor_aria_statements import (
    ManualEditorAriaStatements,
)
from statements.frontend.generation.manual_editor_beforeunload_statements import (
    ManualEditorBeforeUnloadStatements,
)
from statements.frontend.generation.manual_editor_caret_statements import (
    ManualEditorCaretStatements,
)
from statements.frontend.generation.manual_editor_line_break_statements import (
    ManualEditorLineBreakStatements,
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
from statements.frontend.generation.manual_editor_statements import ManualEditorStatements


@pytest.fixture
def chat_workspace_statements():
    return ChatWorkspaceStatements()


@pytest.fixture
def mode_modal_statements():
    return ModeModalStatements()


@pytest.fixture
def manual_editor_statements():
    return ManualEditorStatements()


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
