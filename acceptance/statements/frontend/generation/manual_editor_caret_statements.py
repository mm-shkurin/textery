"""Statements for scenario 3.2 — the toolbar tracks the CARET, not a drag-selection.

The jsdom unit test hand-fired the `select` DOM event via `fireEvent.select`, proving the
handler logic but never that a real browser dispatches a selection event for a caret-only
(non-drag, keyboard-arrow) cursor move. This drives the caret between a bold run and a plain run
with arrow keys and reads the bold button's `aria-pressed`, which only updates if the real
`selectionchange`/`select` the app listens for actually fired.
"""

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait

from statements.frontend.base_frontend_statements import WAIT_TIMEOUT_SECONDS
from statements.frontend.generation.manual_editor_statements import (
    BOLD_BUTTON,
    EDITABLE_CONTENT,
    ManualEditorStatements,
)


class ManualEditorCaretStatements(ManualEditorStatements):
    def type_text_with_leading_bold_run(self, driver, text: str, bold_len: int) -> None:
        """Type `text`, then bold only its first `bold_len` characters via a keyboard selection.

        Home + Shift+Right*n selects the leading run without a pointer drag, then the bold button
        marks it — leaving a bold run followed by a plain run, with no stored-mark ambiguity.
        """
        editable = self._focus_content_area(driver)
        editable.send_keys(text)
        editable.send_keys(Keys.HOME)
        for _ in range(bold_len):
            editable.send_keys(Keys.SHIFT, Keys.ARROW_RIGHT)
        self._wait_for_visible(driver, BOLD_BUTTON).click()

    def move_caret_into_leading_run(self, driver) -> None:
        # Deterministic, no reliance on Home (flaky in this contenteditable): go to the end, then
        # ArrowLeft five times over "aaabbb" — offset 6 -> 1, unambiguously inside the bold "aaa".
        editable = self._wait_for_visible(driver, EDITABLE_CONTENT)
        editable.send_keys(Keys.END)
        for _ in range(5):
            editable.send_keys(Keys.ARROW_LEFT)

    def move_caret_into_trailing_run(self, driver) -> None:
        # End -> offset 6, inside the plain "bbb" run.
        self._wait_for_visible(driver, EDITABLE_CONTENT).send_keys(Keys.END)

    def _wait_for_bold_pressed(self, driver, expected: str) -> None:
        """Poll aria-pressed until it reaches `expected` — the toolbar re-render is async.

        The attribute only flips after ProseMirror dispatches the selection transaction AND React
        re-renders (`shouldRerenderOnTransaction`), which is not synchronous with `send_keys`
        returning. A single immediate read races that flip; polling makes the caret-tracking
        assertion deterministic instead of catching a stale value.
        """
        try:
            WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(
                lambda d: self._wait_for_visible(d, BOLD_BUTTON).get_attribute("aria-pressed")
                == expected
            )
        except TimeoutException:
            pass
        actual = self._wait_for_visible(driver, BOLD_BUTTON).get_attribute("aria-pressed")
        assert actual == expected, (
            f"expected the bold button to reach aria-pressed={expected!r} after the caret move, "
            f"got {actual!r}"
        )

    def assert_bold_button_becomes_active(self, driver) -> None:
        self._wait_for_bold_pressed(driver, "true")

    def assert_bold_button_becomes_inactive(self, driver) -> None:
        self._wait_for_bold_pressed(driver, "false")
