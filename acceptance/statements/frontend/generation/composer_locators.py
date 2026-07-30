"""Topic-composer locators, shared by every flow that reaches the generation surface.

Both the chat-workspace suite (scenario 4.1) and the unified create flow (story 18,
scenario 1.1) drive the same composer — `frontend/src/features/generation/components/Composer.tsx`.
The two testids lived in duplicate, under diverging names (`TOPIC_SEND` vs `TOPIC_SEND_BUTTON`),
which meant a testid rename in the component had two call sites to find and only one obvious one.
"""

from selenium.webdriver.common.by import By

TOPIC_INPUT = (By.CSS_SELECTOR, "[data-testid='topic-input']")
TOPIC_SEND_BUTTON = (By.CSS_SELECTOR, "[data-testid='topic-send']")

# Copy pulled from the built component, not from the stale mockup 04 text.
EXPECTED_TOPIC_INPUT_PLACEHOLDER = "Например: Влияние искусственного интеллекта на образование"
EXPECTED_SEND_BUTTON_TEXT = "Сгенерировать"
