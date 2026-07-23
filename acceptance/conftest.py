import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest
import pytest_asyncio
from selenium import webdriver as selenium_webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions

from clients.application.application_client import ApplicationClient
from statements.auth_statements import AuthStatements
from statements.verify_statements import VerifyStatements
from statements.frontend.auth.login_page_statements import LoginPageStatements
from statements.frontend.auth.register_page_statements import RegisterPageStatements
from statements.frontend.auth.verify_code_page_statements import VerifyCodePageStatements
from statements.frontend.landing_page_statements import LandingPageStatements
from statements.frontend.generation.chat_workspace_statements import ChatWorkspaceStatements
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
from statements.frontend.generation.manual_editor_statements import ManualEditorStatements
from statements.frontend.generation.mode_modal_statements import ModeModalStatements
from statements.frontend.responsive_statements import ResponsiveStatements
from statements.generation_statements import GenerationStatements
from statements.login_statements import LoginStatements
from statements.resend_statements import ResendStatements

# iPhone 12/13-class viewport — the smallest common real-device width the
# "design for phone" scenarios must not horizontally overflow at.
MOBILE_WINDOW_SIZE = "390,844"


@pytest_asyncio.fixture
async def application_client():
    client = ApplicationClient()
    yield client
    await client.close()


@pytest_asyncio.fixture
def generation_statements(application_client):
    return GenerationStatements(application_client)


@pytest_asyncio.fixture
def auth_statements(application_client):
    return AuthStatements(application_client)


@pytest_asyncio.fixture
def verify_statements(application_client):
    return VerifyStatements(application_client)


@pytest_asyncio.fixture
def resend_statements(application_client):
    return ResendStatements(application_client)


@pytest_asyncio.fixture
def login_statements(application_client):
    return LoginStatements(application_client)


@pytest.fixture
def app_url():
    return f"http://127.0.0.1:{os.environ.get('FRONTEND_PORT', '5173')}"


@pytest.fixture
def webdriver():
    options = ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1400,1000")
    # Enables driver.get_log("performance") so Statements can assert on
    # actual network traffic (e.g. duplicate-submission checks) instead of
    # only on DOM state.
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    driver = selenium_webdriver.Chrome(options=options)
    yield driver
    driver.quit()


@pytest.fixture
def mobile_webdriver():
    options = ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument(f"--window-size={MOBILE_WINDOW_SIZE}")
    driver = selenium_webdriver.Chrome(options=options)
    yield driver
    driver.quit()


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

