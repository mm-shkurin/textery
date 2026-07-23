"""Statements for the placeholder RETURNING after a real delete-to-empty.

The jsdom roundtrip unit test clears the editor with `textContent = ''` — a full DOM wipe that
forces a reparse into a guaranteed-empty document. It never travels the real delete-transaction
path a user takes: select-all + Backspace, especially after an Enter has inserted a real
hardBreak NODE (distinct from ProseMirror's view-only trailing-break helper). A residual node
could leave `doc.content.size >= 1`, so the emptiness-keyed placeholder would NOT return and the
user would face a blank, unlabelled box. Only a real browser exercises that path — this drives it.
"""

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver

from statements.frontend.generation.manual_editor_line_break_statements import (
    EDITABLE_CONTENT,
    ManualEditorLineBreakStatements,
)


class ManualEditorPlaceholderDeleteStatements(ManualEditorLineBreakStatements):
    def clear_all_via_backspace(self, driver: WebDriver) -> None:
        """Empty the editor the way a user does: select every character, then Backspace.

        Not a `textContent = ''` DOM wipe — that reparse never runs the delete transaction. This
        goes through ProseMirror's own keymap so a residual hardBreak node (if the delete left
        one) would keep the document non-empty and the placeholder suppressed.
        """
        self.select_all_text_in_editor(driver)
        self._wait_for_visible(driver, EDITABLE_CONTENT).send_keys(Keys.BACKSPACE)
