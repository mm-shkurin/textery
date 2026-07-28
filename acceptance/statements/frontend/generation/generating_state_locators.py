"""Locators and expected copy for story 18, scenario 1.2 — a generating document shows progress.

Locators only, no behaviour: the assertions that consume these live in
`generating_state_statements.py`, which was split at the 200-line cap.
"""

from selenium.webdriver.common.by import By

# The generating surface, marked with this testid by story 18 explicitly as scenario 1.2's
# subject. It renders only on DocArea's `pending` branch, so observing it observes exactly
# the generating state and nothing else.
GENERATING_SURFACE = (By.CSS_SELECTOR, "[data-testid='generation-generating']")

# The two terminal surfaces. Asserted ABSENT so "a generating state is shown" cannot be
# satisfied by a screen that has already moved on: without these the run could complete
# between the send and the check and the test would still be looking at a result it called
# progress.
DOC_BODY = (By.CSS_SELECTOR, "[data-testid='doc-body']")
DOC_ERROR = (By.CSS_SELECTOR, "[data-testid='doc-error']")

# The full visible text of each generating surface, read off the built components rather than
# a mockup. Pinned by equality, not substring: the doc area renders a placeholder in three of
# the four generation states and they differ only by their copy, so a presence-only check
# would pass on the idle placeholder — the one state that means the send never happened.
EXPECTED_GENERATING_DOC_TEXT = (
    "Готовим ваш доклад\nОбычно занимает 1–2 минуты — страница обновится автоматически"
)

# The left panel's Progress view. `ИИ пишет доклад` is rendered ONLY while pending — the
# completed and failed branches replace it — so this is the second, independent witness that
# the surface is the generating one. The typing-dots animation carries no text.
#
# The bare `✦` lines are each step's avatar (`Progress.ChatMsg`), which Selenium reports as its
# own line because avatar and bubble are separate block children. They are kept in the expected
# value rather than filtered out: `.text` is what the user sees, and the failed branch swaps the
# same glyph for `✕`, so dropping them would discard a signal instead of noise.
#
# `ХОД ГЕНЕРАЦИИ` is upper-case because `.chat-panel h3` carries `text-transform: uppercase` and
# Selenium reports RENDERED text — the source says `Ход генерации`. Worth stating: this is the
# one layer that can see it. jsdom applies no CSS, so the renderer-level suite asserts the
# source casing, and the two expected values legitimately differ for the same element.
EXPECTED_GENERATING_PANEL_TEXT = (
    "ХОД ГЕНЕРАЦИИ\n✦\nАнализирую тему и требования\n✦\nИИ пишет доклад"
)
