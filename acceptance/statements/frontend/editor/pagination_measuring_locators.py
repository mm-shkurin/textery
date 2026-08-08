"""Locators and pinned copy for story 10, UI scenario 1.1 — the pre-layout measuring state.

Every element below is one the editor does not render yet; this module is the specification of
what `green-selenium` must be able to find, not a description of today's DOM. Scoped under the
editor shell (`manual-editor`), matching `manual_editor_statements.py`, so a stray element
elsewhere on the page cannot satisfy an assertion about the editor's own surface.

The copy is taken from the measuring mockup (`mockups/desktop/02-measuring.html`) and is pinned
exactly: these are strings the product defines, so visibility alone would accept a blank node or
the wrong state's wording.

Deliberately NOT pinned here: the sheet geometry ("A4, книжная" in the mockup's status bar). That
value comes from the `page_settings` value object (`api-specs/documents_get.yaml`, absent reads as
the default preset), and asserting the preset's label from this scenario would hardcode geometry
the story requires be read from the contract. Geometry is scenario 5.x's subject.
"""

from selenium.webdriver.common.by import By

from statements.frontend.generation.manual_editor_statements import MANUAL_EDITOR_SELECTOR


def _in_editor(testid: str) -> tuple[str, str]:
    return (By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} [data-testid='{testid}']")


# --- The measuring state itself -------------------------------------------------------------
# The surface that replaces the sheets while the font is still loading, plus the things that make
# it recognisable AS measuring rather than as any other non-final state: a skeleton SHEET where
# the laid-out sheet will go, the rail's placeholder rows, and a live progress indicator.
MEASURING_SURFACE = _in_editor("pagination-measuring")
MEASURING_MESSAGE = _in_editor("pagination-measuring-message")
MEASURING_SPINNER = _in_editor("pagination-measuring-spinner")
PAGE_RAIL_SKELETON = _in_editor("page-rail-skeleton")

# The skeleton sheet — the DSL Technical Reference defines the measuring state as exactly
# "Skeleton sheet + rail skeletons, no page count in the status bar", and the mockup renders it as
# placeholder lines inside a sheet-shaped surface. This is the element that carries the POSITIVE
# half of the scenario's third Then: it is what the error state (which shows an error surface) and
# the empty document (which shows a real, blank sheet) do NOT render. Without it, "visibly
# distinct" rests on two absence checks that an editor rendering nothing at all would also satisfy.
SHEET_SKELETON = _in_editor("page-sheet-skeleton")

# The spinner must announce itself as live rather than merely exist: an empty div with the right
# testid is a static notice wearing a spinner's name. `role='status'` + `aria-busy='true'` is also
# what makes the measuring state distinct to a screen reader, where "visibly" has no meaning and
# the error/empty states are told apart by their announced role alone.
EXPECTED_SPINNER_ROLE = "status"
EXPECTED_MEASURING_BUSY = "true"

# --- What must NOT be shown -----------------------------------------------------------------
# `page-count` is the status bar's "Страница N из M" readout. Its ABSENCE is the scenario's
# second Then: a count computed before the document font resolved would be computed on
# substituted metrics and would change under the user afterwards.
PAGE_COUNT = _in_editor("page-count")
# The two states measuring must be distinguishable from. `pagination-error` is scenario 1.3's
# defined outcome; `empty-document-hint` is scenario 2.3's single blank sheet. Measuring is
# neither, and an implementation that renders the empty state while it measures would report
# "1 of 1" pages for a document that has not been laid out.
PAGINATION_ERROR = _in_editor("pagination-error")
EMPTY_DOCUMENT_HINT = _in_editor("empty-document-hint")

# --- The status bar -------------------------------------------------------------------------
# The measuring mockup's status bar reads "Расчёт страниц…" where the paginated one reads
# "Страница 1 из 3" and the empty one "Страница 1 из 1". Pinning this text is the positive half
# of "visibly distinct": absence checks alone would also pass on a blank editor.
PAGINATION_STATUS = _in_editor("pagination-status")

EXPECTED_MEASURING_STATUS = "Расчёт страниц…"
EXPECTED_MEASURING_MESSAGE = "Готовим страницы…"

# The rail shows exactly three placeholder rows while measuring, as the mockup renders them
# (`02-measuring.html`, the three `.skeleton` divs in the rail). Pinned EXACTLY, not as a lower
# bound: this is a RED test, so it is where the claim gets made rather than a description of a DOM
# that already exists. A `>= 1` bound would accept a one-row rail — a different design than the
# one specified — and would silently ratify whichever count green happened to render.
EXPECTED_RAIL_SKELETON_COUNT = 3
