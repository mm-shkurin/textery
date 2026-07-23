"""Statements for scenario 3.2 — the toolbar tracks the CARET, not a drag-selection.

The jsdom unit test hand-fired the `select` DOM event via `fireEvent.select`, proving the
handler logic but never that a real browser dispatches a selection event for a caret-only
(non-drag, keyboard-arrow) cursor move. This drives the caret between a bold run and a plain run
with arrow keys and reads the bold button's `aria-pressed`, which only updates if the real
`selectionchange`/`select` the app listens for actually fired.
"""

from selenium.webdriver.common.keys import Keys

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
        # Home lands at the doc start (inside the bold run); one Right keeps the caret inside it.
        editable = self._wait_for_visible(driver, EDITABLE_CONTENT)
        editable.send_keys(Keys.HOME)
        editable.send_keys(Keys.ARROW_RIGHT)

    def move_caret_into_trailing_run(self, driver) -> None:
        self._wait_for_visible(driver, EDITABLE_CONTENT).send_keys(Keys.END)

    def assert_bold_button_is_inactive(self, driver) -> None:
        button = self._wait_for_visible(driver, BOLD_BUTTON)
        pressed = button.get_attribute("aria-pressed")
        assert pressed == "false", (
            f"expected the bold button to be aria-pressed='false' with the caret in plain text, "
            f"got {pressed!r}"
        )
