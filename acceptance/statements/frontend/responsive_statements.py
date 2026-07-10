from selenium.webdriver.remote.webdriver import WebDriver


class ResponsiveStatements:
    """Assertions shared by every "must not overflow on a phone viewport" scenario."""

    def assert_no_horizontal_overflow(self, driver: WebDriver, label: str) -> None:
        viewport_width = driver.execute_script("return window.innerWidth")
        document_width = driver.execute_script("return document.documentElement.scrollWidth")
        assert document_width <= viewport_width, (
            f"expected {label} to fit within the {viewport_width}px viewport without "
            f"horizontal scroll, but document.documentElement.scrollWidth was {document_width}px"
        )
