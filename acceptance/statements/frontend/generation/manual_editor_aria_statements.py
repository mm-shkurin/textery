"""Statements for the a11y surfaces jsdom pins in the DOM but cannot truly evaluate.

Two owed coverages, both invisible to jsdom by construction:

- The editor's `role="textbox"` + `aria-multiline` + `aria-placeholder` render in the DOM under
  jsdom, but jsdom does not COMPUTE an accessibility tree, so it never proves a browser resolves
  the element to the textbox role assistive tech would announce. Selenium's `aria_role` reads the
  browser's computed role (via CDP), which is that missing proof.

- The `.me-toolbar-btn[aria-expanded='true']` highlight is a CSS rule, and jsdom applies no CSS.
  Opening the link popover with the cursor OUTSIDE a link (so `aria-pressed` is false) must still
  highlight the link button — the highlight coming ONLY from `aria-expanded`. `getComputedStyle`
  in a real browser is the only place that rule is observable.
"""

from selenium.webdriver.common.by import By

from statements.frontend.generation.manual_editor_statements import (
    EXPECTED_PLACEHOLDER_TEXT,
    MANUAL_EDITOR_SELECTOR,
    ManualEditorStatements,
)

EDITOR_CONTENT = (
    By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} [data-testid='editor-content-area']"
)
LINK_BUTTON = (By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} [data-testid='toolbar-link']")

_TRANSPARENT = "rgba(0, 0, 0, 0)"


class ManualEditorAriaStatements(ManualEditorStatements):
    def assert_editor_announces_multiline_textbox(self, driver) -> None:
        content = self._wait_for_visible(driver, EDITOR_CONTENT)
        # The browser's COMPUTED role — the one a screen reader announces — not the raw attribute.
        assert content.aria_role == "textbox", (
            f"expected the editor to compute to the textbox role, got {content.aria_role!r}"
        )
        multiline = content.get_attribute("aria-multiline")
        assert multiline == "true", f"expected aria-multiline='true', got {multiline!r}"
        placeholder = content.get_attribute("aria-placeholder")
        assert placeholder == EXPECTED_PLACEHOLDER_TEXT, (
            f"expected aria-placeholder='{EXPECTED_PLACEHOLDER_TEXT}', got {placeholder!r}"
        )

    def open_link_popover(self, driver) -> None:
        self._wait_for_visible(driver, LINK_BUTTON).click()

    def assert_link_button_highlights_while_popover_open(self, driver) -> None:
        button = self._wait_for_visible(driver, LINK_BUTTON)
        before = button.value_of_css_property("background-color")
        assert before == _TRANSPARENT, (
            f"expected the link button to start unhighlighted (transparent), got {before!r}"
        )

        self.open_link_popover(driver)

        button = self._wait_for_visible(driver, LINK_BUTTON)
        expanded = button.get_attribute("aria-expanded")
        assert expanded == "true", f"expected aria-expanded='true' once the popover opens, got {expanded!r}"
        # The cursor is outside any link (fresh editor has none), so aria-pressed is false — this
        # painted highlight can only come from the aria-expanded rule, the one jsdom cannot see.
        after = button.value_of_css_property("background-color")
        assert after != _TRANSPARENT, (
            f"expected the open popover to paint a highlight on the link button, still {after!r}"
        )
        pressed = button.get_attribute("aria-pressed")
        assert pressed == "false", (
            f"expected aria-pressed='false' (cursor outside a link), got {pressed!r} — "
            "highlight would be ambiguous between the pressed and expanded rules"
        )
