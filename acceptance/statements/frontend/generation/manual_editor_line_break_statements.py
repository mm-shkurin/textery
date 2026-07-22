"""Statements for the line-break (Enter) behavior of the manual editor.

Split from `manual_editor_statements.py`, which is already at 118 lines.

Everything here is about what a REAL browser does with an Enter keystroke, which is the whole
point of driving it in Selenium: the jsdom unit tests reach the editor through a synthetic
`keyDown`, so they exercise the keymap but never ProseMirror's own contenteditable input
handling. A double-insert (keymap AND browser both producing a break) is invisible there and
visible here.
"""

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver

from statements.frontend.generation.manual_editor_statements import (
    EDITABLE_CONTENT,
    ManualEditorStatements,
)

# ProseMirror appends this to an empty line so the caret has somewhere to sit. It is a view-only
# artifact: it never reaches the document model and never appears in the saved HTML, so every
# assertion about breaks must exclude it or it would count as content.
_CARET_HELPER_BREAK = '<br class="ProseMirror-trailingBreak">'

_CONTENT_HTML_SCRIPT = (
    "return document.querySelector('[data-testid=\"editor-content-area\"]').innerHTML"
)

# Counts DISTINCT rendered text baselines, not markup. A `<br>` present in the DOM but not
# breaking the line visually (a CSS regression) would pass an HTML assertion and fail this one.
_VISUAL_LINE_COUNT_SCRIPT = (
    "const editor = document.querySelector('[data-testid=\"editor-content-area\"]');"
    "const range = document.createRange();"
    "range.selectNodeContents(editor);"
    "return new Set([...range.getClientRects()].map((rect) => Math.round(rect.top))).size"
)


class ManualEditorLineBreakStatements(ManualEditorStatements):
    def continue_typing_in_editor(self, driver: WebDriver, text: str) -> None:
        """Types at the CURRENT caret position, without clicking first.

        `type_text_in_editor` focuses by clicking, and a click places the caret where the
        pointer landed — after an Enter that is the previous line, not the new one, so the
        continuation lands before the break and the assertion reads a break that moved. Any
        multi-keystroke sequence must click once (to focus) and then keep typing.
        """
        self._wait_for_visible(driver, EDITABLE_CONTENT).send_keys(text)

    def press_enter_in_editor(self, driver: WebDriver, times: int = 1) -> None:
        editable = self._wait_for_visible(driver, EDITABLE_CONTENT)
        for _ in range(times):
            editable.send_keys(Keys.ENTER)

    def _content_html_without_caret_helper(self, driver: WebDriver) -> str:
        return driver.execute_script(_CONTENT_HTML_SCRIPT).replace(_CARET_HELPER_BREAK, "")

    def assert_editor_content_html_is(self, driver: WebDriver, expected: str) -> None:
        actual = self._content_html_without_caret_helper(driver)
        assert actual == expected, f"expected editor content HTML '{expected}', got '{actual}'"

    def assert_break_count_is(self, driver: WebDriver, expected: int) -> None:
        """Guards the double-insert this whole test exists for: a browser that ran both the
        keymap and its own contenteditable handler yields two breaks per keystroke, and only a
        count assertion catches it — "a break appears" passes either way.
        """
        actual = self._content_html_without_caret_helper(driver).count("<br>")
        assert actual == expected, f"expected exactly {expected} <br> in content, got {actual}"

    def assert_visual_line_count_is(self, driver: WebDriver, expected: int) -> None:
        actual = driver.execute_script(_VISUAL_LINE_COUNT_SCRIPT)
        assert actual == expected, (
            f"expected content to render as {expected} visual line(s), got {actual}"
        )
