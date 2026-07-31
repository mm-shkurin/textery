"""Browser-facing fixtures: the app URL and the two Chrome drivers.

Split out of the root conftest, which had grown past the 200-line file limit.
Registered as a plugin from that conftest, so fixture scope is unchanged.
"""

import os

import pytest
from selenium import webdriver as selenium_webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions

# iPhone 12/13-class viewport — the smallest common real-device width the
# "design for phone" scenarios must not horizontally overflow at.
MOBILE_WINDOW_SIZE = "390,844"


@pytest.fixture
def app_url():
    return f"http://127.0.0.1:{os.environ.get('FRONTEND_PORT', '5173')}"


@pytest.fixture
def webdriver():
    options = ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1400,1000")
    # Enables driver.get_log("performance") so Statements can assert on
    # actual network traffic (e.g. duplicate-submission checks) instead of
    # only on DOM state.
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    driver = selenium_webdriver.Chrome(options=options)
    yield driver
    driver.quit()


@pytest.fixture
def mobile_webdriver():
    options = ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument(f"--window-size={MOBILE_WINDOW_SIZE}")
    driver = selenium_webdriver.Chrome(options=options)
    yield driver
    driver.quit()
