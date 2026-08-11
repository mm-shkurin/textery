"""Whether a chat row is actually ON SCREEN inside the scrolling history, not merely rendered.

Split from `restored_conversation_statements.py` at the 200-line limit, and at a real seam: that
module NARRATES scenario 1.2's steps, this one MEASURES the browser. The measurement is the part
with no Gherkin in it — it is geometry that any future scenario about scroll position (7.x's
"jump to latest", a streaming reply pinning the view) needs in exactly this form.

**Why geometry at all, and never `is_displayed()`.** Selenium reports a row scrolled far below
the bottom of an `overflow-y: auto` container as displayed — the row has a non-zero box and no
`display: none` ancestor — so a check built on it passes on the very layout these assertions
exist to reject. Rects are the only thing that distinguishes "rendered" from "in view".
"""

from typing import Any

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

# Sub-pixel slack for the comparisons below. Rects are fractional CSS pixels and a row flush
# against an edge routinely measures a few hundredths past it; a strict `<=` would fail on
# rounding rather than on scroll position. One pixel is far below the ~40px a single hidden
# bubble would cost, so nothing real hides inside the tolerance.
EDGE_TOLERANCE_PX = 1.0

# Reads both rects in ONE round trip, so the numbers describe one layout rather than two moments.
# `scrollHeight`/`clientHeight` come along because they are what proves the assertion is not
# vacuous: on a conversation that fits, "visible without scrolling" is true of every row and pins
# nothing.
MEASURE_SCRIPT = """
const list = arguments[0], row = arguments[1];
const l = list.getBoundingClientRect(), r = row.getBoundingClientRect();
return {
  scrollHeight: list.scrollHeight, clientHeight: list.clientHeight,
  scrollTop: list.scrollTop,
  listTop: l.top, listBottom: l.bottom, rowTop: r.top, rowBottom: r.bottom,
};
"""


def measure(driver: WebDriver, message_list: WebElement, row: WebElement) -> dict[str, Any]:
    return driver.execute_script(MEASURE_SCRIPT, message_list, row)


def assert_the_history_overflows(box: dict[str, Any]) -> None:
    """The non-vacuity gate, asserted BEFORE the in-view claim it qualifies.

    If the seeded conversation fits in the panel, every row is trivially in view and the
    in-view assertion proves nothing — so that case fails HERE, naming its own causes, rather
    than passing and reporting a scroll behavior nobody tested.
    """
    assert box["scrollHeight"] > box["clientHeight"], (
        f"the chat history does not overflow (scrollHeight={box['scrollHeight']} <= "
        f"clientHeight={box['clientHeight']}), so 'visible without scrolling' is vacuous here. "
        f"Two causes: either the seeded conversation is too short — lengthen SEED_INSTRUCTIONS "
        f"in conversation_transcript.py — or the window is under the 900px breakpoint, below "
        f"which DocumentEditorPage.css drops the grid to height:auto and .ac-chat to "
        f"overflow:visible, leaving .ac-chat-history unbounded and the whole check meaningless"
    )


def assert_the_row_is_fully_in_view(box: dict[str, Any], what: str) -> None:
    """BOTH edges of the row lie inside the history's visible box.

    Bottom alone would accept a message so tall that its top is above the fold — the user sees
    the tail of a reply whose beginning is out of view and cannot tell it began. `visible` means
    the whole row.
    """
    assert box["rowTop"] >= box["listTop"] - EDGE_TOLERANCE_PX, (
        f"{what} starts above the visible top of the chat history "
        f"(rowTop={box['rowTop']}, listTop={box['listTop']}, "
        f"scrollTop={box['scrollTop']}) — its beginning is scrolled out of view"
    )
    assert box["rowBottom"] <= box["listBottom"] + EDGE_TOLERANCE_PX, (
        f"{what} ends below the visible bottom of the chat history "
        f"(rowBottom={box['rowBottom']}, listBottom={box['listBottom']}, "
        f"scrollTop={box['scrollTop']}) — the user must scroll to reach it"
    )
