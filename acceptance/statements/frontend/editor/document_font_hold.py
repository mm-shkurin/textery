"""The lever that puts the document font into the "still loading" state scenario 1.1 needs.

Scenario 1.1's Given is a font that has NOT FINISHED loading — not one that failed (that is 1.3)
and not one that resolved (that is 1.2). Those three are different states, and a test that cannot
tell them apart pins none of them.

Why an installed stub rather than a network lever. `Network.setBlockedURLs` — the lever
`manual_editor_export_error_statements.py` uses for the export GET — makes the request FAIL, so
`document.fonts.ready` RESOLVES and the face falls back to substituted metrics. That is scenario
1.3's Given, and using it here would silently test the wrong scenario. Throttling is worse: it
turns the Given into a race between the font's arrival and the assertion's timeout, and the whole
point of this story's font handling is that a page count computed on substituted metrics is
indistinguishable from a correct one (see `summaries/spec-phase.md` — an unresolvable face does
not error, it substitutes and succeeds). A stub that never settles makes the Given a fact rather
than a timing hope.

Installed through CDP `Page.addScriptToEvaluateOnNewDocument`, which runs before any app script on
EVERY document created after it — required here because `_establish_logged_in_precondition`
navigates twice before the editor is ever reached, and the app reads font readiness during its own
boot. The objection recorded in `auto_editor_transition_witness.py` (it only runs on a NEW
document, so an in-place SPA path never executes it) does not apply: this is installed BEFORE the
first navigation, not after one.
"""

from selenium.webdriver.remote.webdriver import WebDriver

# Replaces the FontFaceSet's readiness surface on the instance, shadowing the prototype getter.
# `ready` never settles, `check` reports every face as unavailable, and `load` hands back the same
# pending promise — the three ways a client can ask "is the document font here yet?".
HOLD_DOCUMENT_FONT_SCRIPT = """
(() => {
  const pending = new Promise(() => {});
  const fonts = document.fonts;
  Object.defineProperty(fonts, 'ready', {configurable: true, get: () => pending});
  fonts.load = () => pending;
  fonts.check = () => false;
  window.__acceptanceDocumentFontHeld = true;
})();
"""

# Proves the Given is real at the moment the assertions run, rather than assumed from the install.
#
# Deliberately NOT a wall-clock wait. The obvious version — set a flag in `.then()` and read it
# after `setTimeout(..., 250)` — proves nothing on the side that matters: if the hold had been
# LOST, `document.fonts.ready` might simply not have resolved within 250 ms yet, `settled` would
# read false, and the scenario would report a Given it does not have. A fixed timer can only ever
# produce weak evidence for a negative.
#
# Instead the promise is raced against a chain of microtask turns. A promise that is ALREADY
# resolved schedules its continuation on the microtask queue immediately, so it wins a race
# against a chain of empty turns; one that is pending cannot win at any number of turns. The
# result is deterministic rather than timing-dependent, and it is correct in both directions.
MICROTASK_RACE_TURNS = 10

READ_DOCUMENT_FONT_STATE_SCRIPT = """
const done = arguments[0];
const turns = arguments[1];
let settled = false;
document.fonts.ready.then(() => { settled = true; });
let chain = Promise.resolve();
for (let i = 0; i < turns; i++) { chain = chain.then(() => {}); }
chain.then(() => done({
  installed: window.__acceptanceDocumentFontHeld === true,
  settled: settled,
  reportsLoaded: document.fonts.check('1em serif'),
}));
"""

# The one state the page may be in for this scenario's Given to hold.
FONT_HELD_MID_LOAD = {"installed": True, "settled": False, "reportsLoaded": False}


class DocumentFontHoldMixin:
    """Hold the document font mid-load, and prove it is still held. Mixed into a Statements."""

    def hold_the_document_font_mid_load(self, driver: WebDriver) -> None:
        """Install the hold. MUST be called before the first navigation of the test."""
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument", {"source": HOLD_DOCUMENT_FONT_SCRIPT}
        )

    def assert_the_document_font_has_not_finished_loading(self, driver: WebDriver) -> None:
        """Assert the Given still holds on the page under test.

        Without this the scenario is only a hope: if the install were dropped, or a navigation
        replaced the document in a way that lost it, every assertion below would run against a
        page whose font HAD resolved — and "the measuring state is shown" would then be a
        failure of the product being tested for the wrong reason, or worse, a pass for one.
        """
        state = driver.execute_async_script(
            READ_DOCUMENT_FONT_STATE_SCRIPT, MICROTASK_RACE_TURNS
        )
        assert state == FONT_HELD_MID_LOAD, (
            f"expected the document font to still be loading — {FONT_HELD_MID_LOAD} — but the "
            f"page reports {state}. `installed` false means the hold never reached this document "
            "(it must be installed before the first navigation); `settled` true means "
            "document.fonts.ready resolved, which is scenario 1.2's Given, not 1.1's; "
            "`reportsLoaded` true means document.fonts.check reported the face as available while "
            "it is supposedly still loading"
        )
