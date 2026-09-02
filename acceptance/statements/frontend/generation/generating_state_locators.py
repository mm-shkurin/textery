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

# The full visible text of the generating surface, read off the built component rather than a
# mockup.
#
# ONE surface now, not two. The screen was redrawn against the customer's frame: the progress
# panel that used to sit beside the document area is gone — the frame draws a single centred
# block while a run is in flight — so both halves of the copy (what is happening and how long it
# takes) are lines of that one block. `EXPECTED_GENERATING_PANEL_TEXT` and `GENERATION_FORM` went with
# the panel they described.
#
# Both type-naming halves below are now COMPUTED, not literal: story 18 scenario 1.2 replaced the
# hardcoded `доклад` with `generatingTitle(documentType)` / `writingProgressMessage(documentType)`
# in `frontend/src/shared/documentTypes.ts`, so these constants transcribe that function's output
# for the one type this scenario picks. Python cannot import the table, so the tie is a test on
# the TS side: `ChatWorkspace.generatingCopy.test.tsx` renders `doklad` and asserts these exact
# strings, expressly so a change to the template or to DOCUMENT_TYPE_ACCUSATIVE fails there rather
# than surfacing here as an unrecognisable "generating state not shown". Change either side and
# that test tells you the other one is stale.
#
# Pinned by equality, not substring: the doc area renders a placeholder in three of
# the four generation states and they differ only by their copy, so a presence-only check
# would pass on the idle placeholder — the one state that means the send never happened.
EXPECTED_GENERATING_DOC_TEXT = (
    "Готовим ваш доклад
ИИ пишет доклад — обычно 1–2 минуты, страница обновится автоматически"
)
