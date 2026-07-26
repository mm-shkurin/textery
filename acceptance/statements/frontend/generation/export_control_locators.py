"""Shared export-control testid locators.

Extracted so both the display/in-flight/progress statements
(manual_editor_export_control_statements.py) and the 3.2 error statements
(manual_editor_export_error_statements.py) can reference the same locators without either module
importing the other (which would be a circular import).
"""

from selenium.webdriver.common.by import By

from statements.frontend.generation.manual_editor_statements import MANUAL_EDITOR_SELECTOR

EXPORT_TRIGGER = (
    By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} [data-testid='export-control-trigger']"
)
EXPORT_OPTION_PDF = (
    By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} [data-testid='export-option-pdf']"
)
EXPORT_OPTION_DOCX = (
    By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} [data-testid='export-option-docx']"
)
