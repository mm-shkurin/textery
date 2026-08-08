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
- [x] red-frontend — RED as predicted: `Error: Not implemented` thrown by the
  `derivePaginationState` stub (`frontend/src/features/editor/logic/paginationState.ts`),
  before any `expect` runs. The pure leg pins the pre-layout *state machine* given supplied
  heights — jsdom measures nothing, so geometry stays with `green-selenium` (Coverage note
  above). `/test-review` found three defects, all the same family as the selenium leg's:
  (a) **`railSkeletonCount: 3` collided with `blockHeights.length === 3`** — three rail rows
  is a fixed design constant, but with a 3-block fixture `railSkeletonCount =
  blockHeights.length` passes, and a 7-block document would then render 7 rows.
  (b) **`sheetSkeletonCount: 1` collided with `ceil(540/900) === 1`** — the header comment
  claimed a geometry-only implementation "would pass nothing", yet such an implementation
  emitted `1` and passed that field. Both fixed by one fixture change: 7 blocks totalling
  2800px against 900px usable, so no expected value (`1`, `3`) is reachable by computing on
  the input. Expected values themselves were not weakened.
  (c) **"Same vocabulary as the selenium leg" was claimed, not held.** `red-selenium` pins
  `"Расчёт страниц…"` / `"Готовим страницы…"`; neither had a home in `PaginationViewState`.
  That is the half of Then 3 that separates measuring from an *empty document* — scenario 2.3
  also shows exactly one sheet, so `sheetSkeletonCount: 1` does not distinguish them; the
  status copy does. Added `statusText` + `measuringMessage` and asserted both.
  Deliberately NOT applied: the `liveRegionRole: 'status' | null` nullability smell — a
  domain-modeling preference owned by `/refactor`, not a loose assertion.
- [~] red-frontend (agent-review CONCERNS 2 + premortem CREDIBLE 1, both independently, the
  second by mutation) — **the scenario's central claim is pinned by nothing.** The suite has
  exactly one case, `fontStatus: 'pending'`, and after the fixture widening EVERY expected
  field is a constant. Premortem replaced the stub body with a frozen literal that ignores
  its argument entirely and unskipped: `Tests 1 passed`. So `derivePaginationState` may
  discard `fontStatus` and be fully green — "having measurements is not permission to
  paginate" is asserted by the header comment, not by a test. The commit message's "only
  phase and pageCount were catching it" is now "nothing is catching it". Add a second case
  over the SAME `blockHeights`/`usableContentHeight` asserting `fontStatus: 'resolved'`
  leaves the measuring phase (`pageCount` non-null), which makes `fontStatus` load-bearing
  and kills the constant-return. This also retires agent-review finding 3: `'resolved'` is
  currently a declared-but-untouched union member, against `tdd-rules.md`'s RED minimality.
  Do NOT wait for scenario 1.2 to supply this — a constant-return green shipped now becomes
  1.3's *actual behavior* (the permanent spinner that 1.3 exists to forbid), and 1.3's red
  would then be written against an implementation that already looks finished.
- [ ] red-frontend (agent-review CONCERNS 1) — **`statusText` carries the page count in
  prose, which is the exact failure the selenium leg's two-node model exists to catch.**
  `red-selenium` splits the status bar into `pagination-status` (`"Расчёт страниц…"`) and
  `page-count` (`"Страница N из M"`), and `pagination_measuring_statements.py:88-91` names
  why: "a missing `page-count` node with a status bar already reading 'Страница 1 из 1'
  would satisfy a pure absence check while telling the user a page count in prose." The
  field added to fix `/test-review` defect (c) declares in its own doc comment that the
  empty phase's `statusText` IS `"Страница 1 из 1"` — so the view state now holds that fact
  twice (`pageCount: 1` and `statusText`), with no rule saying which node renders which.
  Nothing pins `statusText` outside the measuring phase and nothing pins the field→testid
  mapping at all. Pin it before green picks a rendering; scenario 2.3 is otherwise the first
  step that would expose it, by which point the choice is made.
- [ ] green-frontend — **name the consuming component here, as a deliverable** (premortem
  CREDIBLE 2). This commit opened a new feature root, `frontend/src/features/editor/`,
  holding only `logic/`; the real editor is `features/generation/components/ManualEditor.tsx`
  and `grep -l pagination frontend/src --include=*.tsx` returns nothing. A pure function can
  be implemented, correct, and imported by no component — the vitest leg is satisfied either
  way, and the only thing that would catch the disconnect is `green-selenium`, a full work
  unit later (after `align-design`). Green must land a component test asserting the editor
  renders `data-testid="pagination-measuring"` while fonts are pending.
  Also (premortem CREDIBLE 3): `"Расчёт страниц…"` / `"Готовим страницы…"` already exist as
  four independent literals — this test, `pagination_measuring_locators.py:69-70`,
  `mockups/desktop/02-measuring.html:55,73`, `ui-conventions.md:188` — both assertion sites
  exact-match, cross-language, one invisible U+2026 apart. Defect (c) WAS this drift and the
  fix added a fourth copy. Green must not type a fifth: the component imports the literal
  from `paginationState.ts`.
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
