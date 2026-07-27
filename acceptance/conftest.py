import asyncio
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
from statements.frontend.responsive_statements import ResponsiveStatements
from statements.document_export_statements import DocumentExportStatements
from statements.document_export_format_statements import DocumentExportFormatStatements
from statements.document_export_docx_statements import DocumentExportDocxStatements
from statements.document_export_filename_statements import (
    DocumentExportFilenameStatements,
)
from statements.document_export_no_mutation_statements import (
    DocumentExportNoMutationStatements,
)
from statements.generation_statements import GenerationStatements
from statements.login_statements import LoginStatements
from statements.oauth_statements import OAuthStatements
from statements.resend_statements import ResendStatements

# Frontend generation fixtures live in their own module to keep this file under the
# 200-line cap; re-imported here so pytest discovers them as conftest fixtures.
from frontend_generation_fixtures import (  # noqa: F401
    chat_workspace_statements,
    mode_modal_statements,
    manual_editor_statements,
    manual_editor_line_break_statements,
    manual_editor_save_payload_statements,
    manual_editor_placeholder_delete_statements,
    manual_editor_aria_statements,
    manual_editor_caret_statements,
    manual_editor_save_queue_statements,
    manual_editor_popover_clip_statements,
    manual_editor_beforeunload_statements,
)

# iPhone 12/13-class viewport — the smallest common real-device width the
# "design for phone" scenarios must not horizontally overflow at.
MOBILE_WINDOW_SIZE = "390,844"

# OAuth invariant-gate environment contract (see acceptance/tests/backend/oauth/).
HANDOFF_CODE_TTL_ENV_VAR = "OAUTH_HANDOFF_CODE_TTL_SECONDS"
PROVIDER_SECRET_ENV_VAR = "YANDEX_CLIENT_SECRET"
MAX_TESTABLE_TTL_SECONDS = 10


@pytest_asyncio.fixture
async def application_client():
    client = ApplicationClient()
    yield client
    await client.close()


@pytest_asyncio.fixture
def generation_statements(application_client):
    return GenerationStatements(application_client)


@pytest_asyncio.fixture
def document_export_statements(application_client):
    return DocumentExportStatements(application_client)


@pytest_asyncio.fixture
def document_export_format_statements(application_client):
    return DocumentExportFormatStatements(application_client)


@pytest_asyncio.fixture
def document_export_docx_statements(application_client):
    return DocumentExportDocxStatements(application_client)


@pytest_asyncio.fixture
def document_export_filename_statements(application_client):
    return DocumentExportFilenameStatements(application_client)


@pytest_asyncio.fixture
def document_export_no_mutation_statements(application_client):
    return DocumentExportNoMutationStatements(application_client)


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


@pytest_asyncio.fixture
def oauth_statements(application_client):
    return OAuthStatements(application_client)


@pytest_asyncio.fixture
async def expired_code(oauth_statements):
    """A handoff code that has outlived its TTL.

    The TTL is real production config, not a test switch — the acceptance stack runs a
    deliberately tiny one so the boundary is observable in seconds. A long TTL makes
    this invariant untestable rather than passing, so it fails loudly instead.
    """
    ttl_seconds = int(os.environ.get(HANDOFF_CODE_TTL_ENV_VAR, "0"))
    assert 0 < ttl_seconds <= MAX_TESTABLE_TTL_SECONDS, (
        f"the TTL invariant needs {HANDOFF_CODE_TTL_ENV_VAR} set to at most "
        f"{MAX_TESTABLE_TTL_SECONDS}s for the acceptance stack, got {ttl_seconds!r}"
    )
    code = await oauth_statements.handoff_code()
    await asyncio.sleep(ttl_seconds + 1)
    return code


@pytest.fixture
def provider_secret():
    secret = os.environ.get(PROVIDER_SECRET_ENV_VAR, "")
    assert secret, (
        f"the log-leak invariant needs the real {PROVIDER_SECRET_ENV_VAR} in the "
        "acceptance environment — it is the string that must never appear in a log"
    )
    return secret


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



