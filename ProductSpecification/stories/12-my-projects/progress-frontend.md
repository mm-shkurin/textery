# Story 12: Мои проекты — Frontend Progress

Layer: frontend (`frontend/`, `acceptance/tests/frontend/`). Backend progress lives in
`progress-backend.md` — never edited from this session.

Scenarios from `tests/02_UI_Tests.md` (25). The feed reads `GET /api/v1/projects` and the
repeat control posts `POST /api/v1/generations/{id}/repeat` — **neither endpoint exists
yet** (see `endpoints.md`). Frontend work builds against a mock of both; every
`red-selenium`/`green-selenium` leg is backend-gated and is expected to be deferred `[S]`
until the backend lands, then batched into one full-stack selenium pass (same convention as
Story 7 and Story 16). Decide the deferral per scenario at its work unit — do not pre-mark.

## Frontend Scenarios (02_UI_Tests.md)

### 1.1: The feed renders the user's work as cards
- [S] red-selenium — backend-gated (`GET /api/v1/projects` does not exist), deferred to the full-stack selenium pass
- [x] red-frontend
- [x] green-frontend
- [x] red-frontend-api
- [x] green-frontend-api
- [x] align-design
- [x] red-frontend (coverage: unknown wire type gets blue accent)
- [S] green-frontend (coverage: unknown wire type gets blue accent) — zero production files need
  modification: the fallback shipped with `ProjectCard` in 1ad55a5a and was untested, not
  unwritten, so the red test passes on arrival and there is no red state to hand off
- [x] red-frontend (coverage: older project's date carries the year) — assert the mockup's own
  literal (`2 сентября 2025`, no ` г.`); `{day, month, year}` on ru-RU emits the era suffix, so a
  test written to satisfy the branch rather than the mockup would enshrine it
- [x] green-frontend (coverage: older project's date carries the year) — one assertion covers one
  month, so a fix that hand-rolls a Russian genitive month table ships eleven unread entries.
  Keep the formatter and strip the suffix (or omit `year` and append it), do not replace
  `toLocaleDateString`
- [x] red-frontend (a second older year, a second month) — `/^16 декабря 2024$/`, the mockup's own
  literal, pins a second month and a second year in one assertion and kills the hand-rolled-table
  fix as a green option
- [S] green-frontend (a second older year, a second month) — zero production files need modification:
  the previous unit's `formatCardDate` appends `getFullYear()` to a `toLocaleDateString` day+month, so
  it is month- and year-agnostic and the assertion is satisfied on arrival. Same precedent as the
  unknown-wire-type accent pair above — a regression pin, not a red state
- [x] red-frontend (the card shows updatedAt, not createdAt) — every fixture sets the two to the
  same string, so swapping the field the card reads leaves the whole suite green. `12_MyProjects.md`
  makes them equal only at birth and names `updated_at` a sort key
- [S] green-frontend (the card shows updatedAt, not createdAt) — zero production files need
  modification: `ProjectCard.tsx` already reads `project.updatedAt`. Verified discriminating by
  swapping the line to `createdAt` — exactly the new test failed (`5 марта 2024` against
  `/^15 июля$/`), the other four stayed green, which is the aliasing this step existed to kill
- [x] red-frontend (an unparseable updatedAt does not render `Invalid Date NaN`) — premortem finding
  on ce3e04a5, not otherwise queued. `NaN !== currentYear` is true, so a bad date takes the
  year-showing branch and concatenates two failure tokens; `null` renders `1 января 1970`, which
  reads as a real date. `projectsApi.ts` passes `item.updated_at` through unvalidated against an
  endpoint the backend has not built
- [~] green-frontend (an unparseable updatedAt does not render `Invalid Date NaN`) — two skipped tests
  to enable, not one: `new Date(null)` is the epoch, a *valid* Date, so an `isNaN(getTime())` check
  alone fixes the malformed arm and leaves `null` rendering `1 января 1970`. Both were verified to fail
  independently on their own received value.

  **CONTRACT DECIDED (user, on the 5b723153 review passes): render `—`, not an empty element.**
  `HistoryPage.tsx`'s `formatDate` already returns `—` for an invalid date and it is shipped; the red
  read mockup silence as spec silence and pinned a third contract. This green therefore REWRITES both
  skipped tests to assert `/^—$/` instead of `toBeEmptyDOMElement()` before enabling them — a test
  change the green phase would normally be forbidden, allowed here only because it is the recorded
  resolution of a review finding against the red, not a green convenience. Note it dissolves the
  card-collapse pair below: `—` occupies a line, so no `min-height` is needed. Guard the INPUT
  (`typeof iso !== 'string'`), not the epoch value
- [ ] red-frontend (a numeric or otherwise non-string updatedAt renders no date) — the shape that
  passes BOTH guards the pair above pins: `new Date(1755000000)` is a valid, non-NaN, non-null Date
  reading `21 января 1970`, so epoch-seconds from the backend would render a confident wrong date on
  every card. A `typeof iso !== 'string'` check ahead of `new Date` closes null, undefined and this in
  one line. Also close the converse hole: nothing yet distinguishes an input guard from an
  epoch-VALUE guard (`getTime() === 0` satisfies both current tests while blanking a real 1970 date)
- [ ] green-frontend (a numeric or otherwise non-string updatedAt renders no date)
- [ ] red-frontend (an unusable date does not collapse the card's height) — premortem on 5b723153. The
  empty-element contract leaves `.project-card-date` at zero height (`ProjectsPage.css`: plain block
  flow, `font-size`/`color` only, no `min-height`), so the card sits ~14px shorter than its row
  neighbours — the alignment the title's line-clamp comment exists to protect. `align-design` for 1.1
  is already `[x]` and no queued step re-runs it
- [ ] green-frontend (an unusable date does not collapse the card's height)
- [ ] red-frontend (История's formatDate does not render the epoch as a real date) — premortem on
  5b723153, cross-screen. `HistoryPage.tsx` guards with `Number.isNaN(d.getTime())`, which is `false`
  for `new Date(null)`, so a null `updated_at` renders `1 января 1970` there today — the exact epoch
  half this story discovered, live in a screen this story did not touch. Its `'—'` arm has no test at
  all (grep for `'—'` in the history tests returns nothing)
- [ ] green-frontend (История's formatDate does not render the epoch as a real date)
- [ ] red-frontend-api (the wire mapper does not transpose created_at and updated_at) — agent-review
  AND premortem both found this on 43f7e498, independently. The card-level de-alias landed above
  `vi.mock('../../api/projectsApi')`, so `projectsApi.ts`'s two adjacent mapping lines can still be
  swapped with the whole repo green: `PROJECT_WIRE` in `projectsApi.test.ts` aliases the pair the same
  way the four card fixtures did. `historyApi.test.ts` already de-aliases its own `DOCUMENT_WIRE` —
  same fix, distinct timestamps
- [ ] green-frontend-api (the wire mapper does not transpose created_at and updated_at)
- [ ] red-frontend (a 31 December evening does not read as next year) — the invariant
  `formatCardDate`'s own comment names, with zero assertions: no fixture has a UTC year differing
  from its local year. Wants the TZ pinned in the vitest config, so it lands with that
- [ ] green-frontend (a 31 December evening does not read as next year)
- [ ] red-frontend (unknown type's badge carries the wire string) — the accent test asserts only
  that the badge EXISTS, so an empty chip passes; `documentTypeLabelFromWire`'s unknown arm was
  rendered by that fixture and never looked at
- [ ] green-frontend (unknown type's badge carries the wire string)
- [ ] red-frontend (a prototype-named wire type is still unknown) — `documentTypeFromWire` looks up
  an `Object.fromEntries` map, so `documentTypeFromWire('constructor')` returns a truthy Function,
  takes the recognised arm, and ships `project-card-accent-undefined`: an untinted well and a
  blank badge. Verified in this repo's node. The vocabulary is server-owned and free-form
- [ ] green-frontend (a prototype-named wire type is still unknown)
- [ ] red-frontend (the card test's clock is pinned) — `/^15 июля$/` in the pre-existing card test
  reads the wall clock against a hardcoded 2026 fixture, so it fails on 1 Jan 2027 with no code
  change. `vi.setSystemTime`, as the new accent block already does
- [ ] green-frontend (the card test's clock is pinned)
- [ ] red-frontend (coverage: unmount mid-flight sets no state)
- [ ] green-frontend (coverage: unmount mid-flight sets no state)
- [ ] green-selenium
- [ ] demo

### 1.2: An untitled document shows its first line instead of a type label
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 1.3: The list view shows the same work as rows
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 1.4: «Недавние проекты» shows the newest work above the full list
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 1.5: Out-of-scope controls are inert
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 2.1: Searching narrows the feed
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 2.2: A search matching nothing offers to clear the search
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 2.3: A user with no work at all is offered to create a project
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 2.4: Typing does not fire one request per keystroke
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 2.5: A slow earlier search never overwrites a newer one
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 3.1: Changing the sort reorders the feed
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 3.2: Changing the sort keeps the search and returns to the first page
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 4.1: The feed shows a skeleton while it loads
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 4.2: A failed load offers a retry without blanking the page
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 4.3: Repeated retries against a failing backend back off
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 5.1: A failed generation is shown as a card with a repeat action
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 5.2: Repeating leaves the original card and adds one new one
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 5.3: A double-click repeats once
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 5.4: A failed repeat leaves no phantom card
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 5.5: Repeating work that has since finished refreshes instead of dead-ending
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 6.1: Opening a project card opens it in the editor
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 6.2: Returning from the editor restores the search, sort, and view
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 6.3: The chosen view survives a reload
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 6.4: A corrupted stored view falls back to the default
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 6.5: The empty state's create action reaches the create flow
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo
