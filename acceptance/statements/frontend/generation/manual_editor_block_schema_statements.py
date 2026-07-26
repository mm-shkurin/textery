"""Statements for the block-schema live round-trip (Editor Extension E1.1).

The jsdom block-schema tests prove `editor.getHTML()`/serialize produces semantic block
elements, but never that those blocks survive a real browser build → `PUT` → backend
store → `GET`. A sanitizer or a parse rule on either side could reshape an `<h1>` into a
`<p>`, or drop a heading, and the user would reopen flattened prose — the exact data loss
the render-only assertions cannot see.

So this builds multi-block content in a real browser (paragraphs + H1/H2/H3, created via
StarterKit's markdown input rules since the toolbar exposes only H3), saves it, and reads
it back through the backend's own `GET /api/v1/documents/{id}` — the true round-trip a
reopen takes. Content is asserted as an exact serialized string so a reordered, dropped, or
demoted block fails loudly rather than passing on a membership-blind substring check.
"""

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver

from statements.frontend.generation.manual_editor_save_payload_statements import (
    ManualEditorSavePayloadStatements,
)

# Each entry is (markdown prefix typed to trigger the StarterKit input rule, text, expected
# serialized element). An empty prefix stays a paragraph. The order is the document order the
# read-back must return unchanged.
_BLOCKS = [
    ("# ", "Heading one", "<h1>Heading one</h1>"),
    ("## ", "Heading two", "<h2>Heading two</h2>"),
    ("### ", "Heading three", "<h3>Heading three</h3>"),
    ("", "A closing paragraph.", "<p>A closing paragraph.</p>"),
]

EXPECTED_BLOCK_CONTENT = "".join(expected for _prefix, _text, expected in _BLOCKS)


class ManualEditorBlockSchemaStatements(ManualEditorSavePayloadStatements):
    def build_multi_block_document(self, driver: WebDriver) -> None:
        """Type paragraphs + H1/H2/H3 as distinct blocks.

        The input rule fires on the space after the `#`s, promoting the current (empty)
        paragraph to the heading node; Enter then splits into a fresh paragraph for the next
        block. The final paragraph carries no trailing Enter, so no empty trailing block is
        created for serialize to strip — the read-back is exactly the four authored blocks.
        """
        editable = self._focus_content_area(driver)
        for index, (prefix, text, _expected) in enumerate(_BLOCKS):
            editable.send_keys(prefix + text)
            if index < len(_BLOCKS) - 1:
                editable.send_keys(Keys.ENTER)

    def assert_saved_blocks_round_trip_as_semantic_html(self, driver: WebDriver) -> None:
        content = self.read_back_saved_content(driver)
        assert content == EXPECTED_BLOCK_CONTENT, (
            "expected the saved blocks to round-trip as their exact semantic elements "
            f"{EXPECTED_BLOCK_CONTENT!r}, got {content!r}"
        )
