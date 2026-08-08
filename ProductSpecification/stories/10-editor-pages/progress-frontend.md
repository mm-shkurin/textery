# Story 10 — Frontend Progress

Story-level narrative and decisions: `progress.md`. Backend and the rest:
`progress-backend.md`.

Scenario ids map to `tests/02_UI_Tests.md`.

**Sequencing note.** The concern this note originally raised was pagination written against
hardcoded constants — rewritten, tests included, the moment settings land. That concern is
answered by the *contract*, not by the backend implementation, and the contract is closed:
`page_settings` and its `PageSettings` schema are specified in `api-specs/documents_get.yaml`
and `documents_save.yaml`, with the PUT tri-state rules in `endpoints.md`. Frontend work
reads geometry from that value object, never from constants.

Absent `page_settings` reads as `null`, which the client renders as the default preset — so
the scenarios below run against the backend as it stands today, before scenarios 2.x/4.x
land their storage. The steps that genuinely need stored settings to survive a round-trip
are the `*-frontend-api` ones on scenarios 5.2, 6.1, 7.1, 7.2 and 7.3 (a save that must come
back changed); those wait on `progress-backend.md` scenario 4.x. Everything else does not.

**Coverage note.** Pagination is measured by the browser. jsdom reports every element as
zero-height, so `red-frontend` can only pin the break-decision logic given *supplied*
heights and the settings value object; "does it break in the right place" has meaning only
in `red-selenium` / `green-selenium`. Scenarios whose whole claim is geometric are marked
below — their vitest step covers logic, not layout.

## Frontend Scenarios (02_UI_Tests.md)

### Scenario 1.1: Pagination waits for the document font
- [x] red-selenium — RED as predicted: `TimeoutException`, `[data-testid='manual-editor']
  [data-testid='pagination-measuring']` never appeared; no pre-layout state exists in
  `frontend/src` at all. Three things this step settled, all of which green inherits:
  (a) **The route to the editor is Мои работы → click a row.** `mode-card-manual` — the path
  `manual_editor_statements` uses — is DEAD; story 18 removed the mode modal and that testid
  exists nowhere in production. The document is seeded over HTTP, then opened by clicking.
  No URL navigation.
  (b) **The font lever is not a blocked URL.** Per the journey summary, a font the renderer
  cannot resolve RESOLVES with substituted metrics — that is 1.3's Given, not 1.1's.
  `document_font_hold.py` stubs `fonts.ready` permanently pending via CDP, and the test reads
  the state back off the page so the Given is asserted, not assumed.
  (c) **`/test-review` found the third Then pinned nothing.** "Visibly distinct from an error
  and from an empty document" was two absence checks, which an editor rendering NOTHING
  satisfies. The positive separator is `page-sheet-skeleton` (spec: "Skeleton sheet + rail
  skeletons"; `mockups/desktop/02-measuring.html:61-65`) — it had no locator anywhere. Now
  asserted, along with exactly 3 rail skeletons and `role="status"` + `aria-busy="true"`.
  Absence assertions no longer accept not-yet-rendered as absent.
- [~] red-frontend
- [ ] green-frontend
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 1.2: The page count appears only once the font has resolved
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] green-selenium
- [ ] demo

### Scenario 1.3: A font that never loads reaches a defined outcome, not a permanent spinner
- [ ] red-frontend
- [ ] green-frontend
- [ ] align-design
- [ ] demo

### Scenario 2.1: Content is laid out on discrete sheets — geometric, Selenium-led
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 2.2: The first page carries no number by default, later pages do
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 2.3: An empty document shows one blank sheet
- [ ] red-frontend
- [ ] green-frontend
- [ ] align-design
- [ ] demo

### Scenario 3.1: The counter follows the caret and updates as the user types — geometric
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] green-selenium
- [ ] demo

### Scenario 3.2: A shortfall against the requested volume is shown
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] demo

### Scenario 4.1: An inserted break starts a new sheet
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 4.2: Editing above a break re-flows the pages without moving the break
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] green-selenium
- [ ] demo

### Scenario 4.3: A break can be selected and deleted
- [ ] red-frontend
- [ ] green-frontend
- [ ] green-selenium
- [ ] demo

### Scenario 5.1: The panel opens with the document's effective settings
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] demo

### Scenario 5.2: Applying a change re-paginates the document
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] green-selenium
- [ ] demo

### Scenario 6.1: A rejected value is reported inline against its own field
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] demo

### Scenario 6.2: An over-length header is refused rather than trimmed
- [ ] red-frontend
- [ ] green-frontend
- [ ] align-design
- [ ] demo

### Scenario 7.1: A failed save is shown differently from a rejected value
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] demo

### Scenario 7.2: A rejected geometry rolls the layout back
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] green-selenium
- [ ] demo

### Scenario 7.3: A late response never replaces newer state
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] demo

### Scenario 7.4: An in-flight action cannot be triggered twice
- [ ] red-frontend
- [ ] green-frontend
- [ ] demo

### Scenario 7.5: Unsaved panel edits are guarded against leaving
- [ ] red-frontend
- [ ] green-frontend
- [ ] demo

### Scenario 8.1: Selecting a page in the rail scrolls to it
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 8.2: The page rail offers no way to create a page
- [ ] red-frontend
- [ ] green-frontend
- [ ] demo
