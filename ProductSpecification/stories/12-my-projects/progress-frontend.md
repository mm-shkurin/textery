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
- [x] green-frontend (an unparseable updatedAt does not render `Invalid Date NaN`) — two skipped tests
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
- [x] red-frontend (a numeric updatedAt, and a real 1970 date, are told apart) — **note revised after
  4abe463e: the production line this step called for is already shipped, untested.** The green wrote
  `typeof iso !== 'string'` when its two tests only forced `iso == null`, so the numeric arm
  (`new Date(1755000000)` — a valid, non-NaN, non-null Date reading `21 января 1970`) returns `—`
  today with zero assertions on it. This red is now two fixtures, not one:
  a numeric `updatedAt` asserting `/^—$/`, and `'1970-01-01T00:00:00Z'` asserting `/^1 января 1970$/`.
  The second is the one that matters — it is the only thing that makes the green's headline argument
  true. Appending `|| date.getTime() === 0` to the validity guard passes all 9 current tests while
  blanking a genuine 1970 date, which is the bug the commit message says it refused to write
- [S] green-frontend (a numeric updatedAt, and a real 1970 date, are told apart) — zero production
  files need modification; the guard shipped early in 4abe463e. Confirm at the work unit rather than
  trusting this line
- [x] red-frontend (a sentinel timestamp does not render as a real date) — premortem on 4abe463e, the
  arm that survives every guard now shipped: `'0001-01-01T00:00:00Z'` renders `1 января 1` and
  `'9999-12-31T23:59:59Z'` renders `1 января 10000`. Both are strings, both are valid Dates. These are
  the two most common backend null-timestamp sentinels (`LocalDate.MIN`, `DateTime.MinValue`, Postgres
  `±infinity`). The 9999 arm is the worse one — 1.4's «Недавние проекты» rail sorts on `updated_at`, so
  one sentinel row takes the top slot permanently and the user's real newest work never surfaces.
  Wants a bounded plausible year, not another shape check
- [x] green-frontend (a sentinel timestamp does not render as a real date) — shipped as
  `EARLIEST_PLAUSIBLE_YEAR = 1900` / `LATEST_PLAUSIBLE_YEAR = 2200`, both fixed constants.
  The ceiling is deliberately NOT `new Date().getFullYear()`: both review passes on 9efff61f
  showed a clock-anchored ceiling blanks the date on a project the user just edited whenever the
  client clock trails the server, and on every 31 December evening. The floor sits below 1970
  because `EPOCH_DATE_PROJECT` reads 1969 in any negative-offset zone. Original note follows: two `it.skip` in
  `ProjectsPage.cardDateBounds.test.tsx`; the fix is a bounded plausible-year branch in
  `formatCardDate`, not another shape check. The lower bound must sit at or below 1970 —
  `EPOCH_DATE_PROJECT` pins `1 января 1970` as a genuinely renderable date. Both arms must go green
  from one change: a lower-bound-only fix leaves `1 января 10000` rendering
- [x] red-frontend-api (the mapper does not silently produce an item with an absent updatedAt) —
  premortem on 4abe463e. Before this commit a broken wire contract rendered `Invalid Date NaN` on every
  card: wrong, but loud and diagnosable from one screenshot. It now renders `—` on every card, which
  looks intentional and could sit in production unnoticed. `projects_schemas.yaml` declares
  `updated_at` required; if the real endpoint lands with `updatedAt`, omits it on the `generation` arm,
  or nests it, `projectsApi.ts` maps `undefined` and every card degrades identically. Nothing
  distinguishes one unusable row from a broken contract. The red belongs at the mapper, not the card
- [x] green-frontend-api (the mapper does not silently produce an item with an absent updatedAt) —
  shipped as `parseUpdatedAt` + exported `MISSING_UPDATED_AT_MESSAGE`. The guard is
  `typeof raw !== 'string' || raw === ''`, not `=== undefined`: agent-review on dbed4e02 showed the
  narrow check passes the test while mapping `null` straight through to the same em dash the guard
  exists to prevent. Only `updated_at` is guarded — the other eight required fields are deliberately
  left for the shaping decision below. Original note follows: 
  contract chosen by the red: `listProjects` REJECTS the whole page with
  `Error('Сервер вернул проект без даты изменения.')`, mirroring `INVALID_VERSION_MESSAGE` /
  `parseVersion` in `generation/api/documentApi.ts`. Rejecting beats dropping the row — a serializer
  that omits a required field on one item is broken for all of them, and a silently short page hides
  that as well as an em dash does. Green MUST export the message constant from `projectsApi.ts`; the
  test currently holds it as a local `EXPECTED_MESSAGE` only because RED may not touch production, and
  the `/refactor` after green replaces the literal with the import or the two definitions drift
- [~] red-frontend (a rejected listProjects does not look like an empty feed) — premortem on dbed4e02,
  and now live rather than hypothetical: the green above ships the rejection, and `ProjectsPage.tsx`'s
  only consumer is `listProjects().then(page => setItems(page.items))` with no `.catch` and no error
  state. A serializer renaming `updated_at` therefore renders an unhandled promise rejection plus a
  page visually identical to «у вас пока нет проектов» — strictly quieter than the `—` the mapper
  guard was written to eliminate. Assert an error element is present AND the feed holds zero cards
- [ ] green-frontend (a rejected listProjects does not look like an empty feed)
- [ ] red-frontend-api (an absent required field other than updated_at is not mapped through) — the
  shaping decision agent-review raised on dbed4e02 and this step defers no further: nine fields are
  required in `projects_schemas.yaml`, one is guarded. `can_repeat` absent fails OPEN — «Повторить» is
  silently never offered. Decide the guard's shape here (one message per field does not extend to
  nine) before adding arms one at a time
- [ ] green-frontend-api (an absent required field other than updated_at is not mapped through)
- [ ] red-frontend (formatRelativeTime does not claim an unusable createdAt was just created) —
  premortem on 4abe463e, the third divergent contract and the only one that states a false fact rather
  than declining to state one. `frontend/src/features/generation/formatRelativeTime.ts` returns
  `'создан только что'` for BOTH `null` and an invalid date, rendered at `DocArea.tsx:40` — so the exact
  wire condition this scenario exists to handle tells the user a six-month-old document was created
  seconds ago. Worse, `formatRelativeTime.test.ts:21,25` pin that behaviour, so the reconciliation pass
  would land with a green test guarding the lie. This step must REWRITE those two assertions; flag it
  as a deliberate test change the way 4abe463e did, or it reads as green-phase convenience
- [ ] green-frontend (formatRelativeTime does not claim an unusable createdAt was just created)
- [S] red-frontend (an unusable date does not collapse the card's height) — dissolved by the em-dash
  contract, not deferred. The premortem raised this on 5b723153 against the EMPTY-element contract,
  which leaves `.project-card-date` at zero height (`ProjectsPage.css`: plain block flow,
  `font-size`/`color` only, no `min-height`) and drops the card ~14px below its row neighbours. `—`
  occupies a line, so the box the alignment depends on is there without a `min-height`. Re-open if the
  placeholder ever becomes empty again
- [S] green-frontend (an unusable date does not collapse the card's height) — see above
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
  from its local year. The TZ pin this step wanted has ALREADY LANDED — `test.env.TZ =
  'Europe/Moscow'` in `vite.config.ts`, pulled forward by the epoch fixture in the cardDate unit,
  which could not be made zone-independent and would otherwise have been red on a US-zone runner.
  Moscow, not UTC, precisely so this step stays writable: it is UTC+3, so a UTC year and a local
  year can still differ. What REMAINS for this step is unchanged and is the whole of its substance
  — a fixture at a late-December evening UTC (e.g. `2025-12-31T21:00:00Z`, which renders
  `1 января 2026` under the pin) plus the assertion that the card shows the LOCAL year, and the
  `formatCardDate` fix if it is red
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
