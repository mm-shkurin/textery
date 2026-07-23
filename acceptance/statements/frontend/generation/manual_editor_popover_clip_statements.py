"""Statements for scenario 7.9 — the link popover must not be clipped by the editor shell.

`.me-link-popover` is `position:absolute; z-index:20`, anchored `left:0` to the link button,
inside `.me-editor-shell { overflow:hidden }`. A z-index cannot escape an ancestor's clip, so if
the button sits far enough right that the 260px popover runs past the shell's right edge, the
overflow is clipped and the URL field / actions become unreachable. jsdom applies no layout, so
only a real browser can measure this.
"""

from selenium.webdriver.common.by import By

from statements.frontend.generation.manual_editor_statements import (
    MANUAL_EDITOR_SELECTOR,
    ManualEditorStatements,
)

LINK_BUTTON = (By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} [data-testid='toolbar-link']")
LINK_POPOVER = (By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} .me-link-popover")

_RECTS_SCRIPT = """
const editor = document.querySelector("[data-testid='manual-editor']");
const shell = editor.querySelector('.me-editor-shell');
const popover = editor.querySelector('.me-link-popover');
const r = (el) => { const b = el.getBoundingClientRect();
  return {left: b.left, top: b.top, right: b.right, bottom: b.bottom}; };
return {
  popover: r(popover),
  shell: r(shell),
  viewport: {width: window.innerWidth, height: window.innerHeight},
};
"""


class ManualEditorPopoverClipStatements(ManualEditorStatements):
    def use_narrow_viewport(self, driver) -> None:
        # A phone-width window: the toolbar wraps and the link button can sit near the right edge,
        # the case the CSS's width-clamp + right-anchor (@media max-width:768px) must survive.
        driver.set_window_size(390, 740)

    def open_link_popover(self, driver) -> None:
        self._wait_for_visible(driver, LINK_BUTTON).click()
        self._wait_for_visible(driver, LINK_POPOVER)

    def measure_popover_geometry(self, driver) -> dict:
        return driver.execute_script(_RECTS_SCRIPT)

    def assert_popover_not_clipped(self, driver) -> None:
        geo = self.measure_popover_geometry(driver)
        popover, shell, viewport = geo["popover"], geo["shell"], geo["viewport"]
        # overflow:hidden on the shell clips anything past its box, so the popover must fit inside
        # the shell's rect (1px tolerance for sub-pixel borders).
        tol = 1.0
        assert popover["left"] >= shell["left"] - tol, f"popover clipped LEFT by shell: {geo}"
        assert popover["top"] >= shell["top"] - tol, f"popover clipped TOP by shell: {geo}"
        assert popover["right"] <= shell["right"] + tol, f"popover clipped RIGHT by shell: {geo}"
        assert popover["bottom"] <= shell["bottom"] + tol, f"popover clipped BOTTOM by shell: {geo}"
        # ...and within the viewport, so it is actually reachable on screen.
        assert popover["left"] >= -tol and popover["top"] >= -tol, f"popover off-screen: {geo}"
        assert popover["right"] <= viewport["width"] + tol, f"popover past viewport right: {geo}"
        assert popover["bottom"] <= viewport["height"] + tol, f"popover past viewport bottom: {geo}"
