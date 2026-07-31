"""Page-object Statements fixtures for the frontend (Selenium) scenarios.

Split out of the root conftest, which had grown past the 200-line file limit.
Registered as a plugin from that conftest, so fixture scope is unchanged.
"""

import pytest

from statements.frontend.auth.login_page_statements import LoginPageStatements
from statements.frontend.auth.register_page_statements import RegisterPageStatements
from statements.frontend.auth.verify_code_page_statements import VerifyCodePageStatements
from statements.frontend.generation.chat_workspace_statements import ChatWorkspaceStatements
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
from statements.frontend.generation.mode_modal_statements import ModeModalStatements
from statements.frontend.landing_page_statements import LandingPageStatements
from statements.frontend.responsive_statements import ResponsiveStatements


@pytest.fixture
def landing_page_statements():
    return LandingPageStatements()


@pytest.fixture
def register_page_statements():
    return RegisterPageStatements()


@pytest.fixture
def login_page_statements():
    return LoginPageStatements()


@pytest.fixture
def verify_code_page_statements():
    return VerifyCodePageStatements()


@pytest.fixture
def responsive_statements():
    return ResponsiveStatements()


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
