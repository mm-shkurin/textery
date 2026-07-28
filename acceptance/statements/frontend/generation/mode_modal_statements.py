"""Mode-modal locators.

Story 18 removed the mode-select modal from the product — picking a document type now goes
straight to generation. The `ModeModalStatements` class that drove it (and its skipped Story 5
acceptance test) has been retired along with the surface.

What survives is the pair of locators below, still used by live suites to assert the modal's
ABSENCE (`generate_flow_statements.assert_no_mode_modal_shown`) or that it is closed
(`manual_editor_statements.assert_mode_modal_is_closed`).
"""

from selenium.webdriver.common.by import By

MODE_MODAL = (By.CSS_SELECTOR, "[data-testid='mode-modal']")
MODE_CARD_MANUAL = (By.CSS_SELECTOR, "[data-testid='mode-card-manual']")
