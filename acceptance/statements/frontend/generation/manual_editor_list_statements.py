"""Statements for the live list round-trip (Editor Extension E2.1).

The jsdom list test proves the toolbar controls wrap a block in a `<ul>`/`<ol>` node, but
never that a list built in a real browser survives `PUT` → backend store → `GET`. A parse
rule or sanitizer on either side could flatten a list to paragraphs, and the user would
reopen their bullets run together as prose — data loss the jsdom render assertion cannot see.

So this builds a bulleted list and a numbered list in a real browser (via StarterKit's
markdown input rules — `- ` starts a bullet list, `1. ` an ordered list — which are on for
this editor), saves, and reads the document back through the backend's own
`GET /api/v1/documents/{id}`. Content is asserted as an exact serialized string so a
flattened, reordered, or demoted list fails loudly.
"""

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver

from statements.frontend.generation.manual_editor_save_payload_statements import (
    ManualEditorSavePayloadStatements,
)

# StarterKit wraps list-item content in a paragraph; serializeEditorHtml strips only a
# trailing empty top-level <p>, so the two lists serialize exactly as below.
EXPECTED_LIST_CONTENT = (
    "<ul><li><p>Bullet one</p></li><li><p>Bullet two</p></li></ul>"
    "<ol><li><p>Number one</p></li><li><p>Number two</p></li></ol>"
)


class ManualEditorListStatements(ManualEditorSavePayloadStatements):
    def build_bulleted_and_numbered_lists(self, driver: WebDriver) -> None:
        """Type a bulleted list, exit it, then a numbered list.

        `- ` promotes the empty first paragraph to a bullet list; Enter on a non-empty item
        adds the next item; Enter on the empty item lifts back out to a paragraph, where
        `1. ` then starts the ordered list.
        """
        editable = self._focus_content_area(driver)
        editable.send_keys("- Bullet one")
        editable.send_keys(Keys.ENTER)
        editable.send_keys("Bullet two")
        editable.send_keys(Keys.ENTER)
        editable.send_keys(Keys.ENTER)  # empty item → lift out of the bullet list
        editable.send_keys("1. Number one")
        editable.send_keys(Keys.ENTER)
        editable.send_keys("Number two")

    def assert_saved_lists_round_trip_as_semantic_html(self, driver: WebDriver) -> None:
        content = self.read_back_saved_content(driver)
        assert content == EXPECTED_LIST_CONTENT, (
            "expected the bulleted and numbered lists to round-trip as their exact semantic "
            f"elements {EXPECTED_LIST_CONTENT!r}, got {content!r}"
        )
