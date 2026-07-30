"""Statements for the live debounced autosave (Editor Extension E3.1).

The jsdom autosave test proves a debounce timer calls `saveDocument` after typing stops, but
under fake timers with a mocked API. It never proves that, in a real browser, stopping typing
actually fires a `PUT` and the backend stores it — with no click on Сохранить. A missing
production timer, a debounce that never re-arms, or a save that silently drops would all pass
the unit test's mock yet lose the user's work in the real app.

So this types in a real browser, NEVER clicks the save button, waits for the app's own
saved-status indicator to turn "saved" on its own, then reads the document back through the
backend's `GET /api/v1/documents/{id}` — proving the debounced autosave both fired and
persisted without any explicit save action.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from statements.frontend.generation.manual_editor_save_payload_statements import (
    ManualEditorSavePayloadStatements,
)
from statements.frontend.generation.manual_editor_statements import MANUAL_EDITOR_SELECTOR

SAVED_STATUS = (By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} .me-save-status--saved")
SAVE_BUTTON = (By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} .me-save-btn")
# The debounce is 1000ms; allow generous headroom for the timer plus the PUT round-trip
# without making the wait so long it hides a debounce that never fires.
_AUTOSAVE_WAIT_SECONDS = 15


class ManualEditorAutosaveStatements(ManualEditorSavePayloadStatements):
    def assert_editor_autosaves_without_a_click(self, driver) -> None:
        # A live guard against a false pass: if a stray click ever crept in, the test would no
        # longer prove "without a click". The save button exists but is never clicked here.
        assert driver.find_elements(*SAVE_BUTTON), "expected the manual save button to be present"
        WebDriverWait(driver, _AUTOSAVE_WAIT_SECONDS).until(
            ec.visibility_of_element_located(SAVED_STATUS)
        )

    def assert_autosaved_content_persisted(self, driver, expected: str) -> None:
        content = self.read_back_saved_content(driver)
        assert content == expected, (
            f"expected the autosaved content to persist as {expected!r}, got {content!r}"
        )
