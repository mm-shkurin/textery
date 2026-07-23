"""Statements for the beforeunload guard's LIVE effect (guard-unsaved-work owe).

What a real browser CAN prove here, and what it cannot:

- CAN: that the guard's `useEffect` actually binds a `beforeunload` listener on the REAL window
  while the document is dirty and REMOVES it once a save leaves it clean — dispatching a genuine
  cancelable event through Chrome's own event system and reading `defaultPrevented` across the
  dirty->clean transition. jsdom asserts the same booleans, but through a simulated event target;
  this proves the real `window` listener + the effect's cleanup fire in a real browser.

- CANNOT (headless limitation, both probed 2026-07-23): the VISIBLE native "Leave site?" dialog
  and the BeforeUnloadEvent STRING `returnValue`. Headless Chrome auto-handles the beforeunload
  dialog on navigation (no catchable alert), and a synthetic `new Event('beforeunload')` exposes
  only the legacy boolean `returnValue` getter (`!defaultPrevented`) in EVERY engine — Chrome
  reported `returnValue: false` exactly as jsdom does. Only a real user-driven navigation creates
  a true BeforeUnloadEvent with the string property, which a headless driver cannot surface. That
  sub-coverage stays a runtime behavior, not an assertable one here.
"""

from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from statements.frontend.base_frontend_statements import WAIT_TIMEOUT_SECONDS
from statements.frontend.generation.manual_editor_save_payload_statements import (
    ManualEditorSavePayloadStatements,
    SAVE_BUTTON,
    SAVED_STATUS,
)

_DISPATCH_BEFOREUNLOAD_PREVENTED = """
const event = new Event('beforeunload', {cancelable: true});
window.dispatchEvent(event);
return event.defaultPrevented;
"""


class ManualEditorBeforeUnloadStatements(ManualEditorSavePayloadStatements):
    def _beforeunload_is_prevented(self, driver) -> bool:
        return driver.execute_script(_DISPATCH_BEFOREUNLOAD_PREVENTED)

    def assert_beforeunload_guard_is_armed(self, driver) -> None:
        assert self._beforeunload_is_prevented(driver) is True, (
            "expected a real-window beforeunload to be cancelled (guard armed) while the "
            "document is dirty, but it was not prevented"
        )

    def assert_beforeunload_guard_is_disarmed(self, driver) -> None:
        assert self._beforeunload_is_prevented(driver) is False, (
            "expected a real-window beforeunload to pass through (guard removed) once the "
            "document is clean, but it was still prevented — the effect cleanup did not run"
        )

    def save_until_clean(self, driver) -> None:
        self._wait_for_visible(driver, SAVE_BUTTON).click()
        WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(
            ec.visibility_of_element_located(SAVED_STATUS)
        )
