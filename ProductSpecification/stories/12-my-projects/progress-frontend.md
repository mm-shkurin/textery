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
- [x] red-frontend (a rejected listProjects does not look like an empty feed) — premortem on dbed4e02,
  and now live rather than hypothetical: the green above ships the rejection, and `ProjectsPage.tsx`'s
  only consumer is `listProjects().then(page => setItems(page.items))` with no `.catch` and no error
  state. A serializer renaming `updated_at` therefore renders an unhandled promise rejection plus a
  page visually identical to «у вас пока нет проектов» — strictly quieter than the `—` the mapper
  guard was written to eliminate. Assert an error element is present AND the feed holds zero cards
- [x] green-frontend (a rejected listProjects does not look like an empty feed) — the RED run showed a
  second, independent symptom of the same missing `.catch`: an **Unhandled Rejection**
  (`Сервер вернул проект без даты изменения.`) alongside the timeout. Both vanish with one fix.
  The test pins the mapper's message verbatim onto the screen via `data-testid="projects-error"`;
  render the caught error's `.message` rather than hardcoding this one constant into the component —
  scenario 4.2 («A failed load offers a retry without blanking the page») arrives wanting a retry
  affordance and would have to undo a hardcoded string.

  **Shipped differently from this note, deliberately.** The catch routes through
  `describeFailure(failure, LOAD_FAILURE_FALLBACK)` (`shared/api/send.ts`), the same call
  `useGeneration.ts:111` makes — not `e.message`. Two reasons the note did not know: `send.ts:93`
  re-throws a 5xx as a bare `HttpError` **object literal**, so `.message` renders `undefined` on a
  path no test exercises; and `SessionExpiredError` reaches `describeFailure` with its type intact
  and returns its own «Сессия истекла. Войдите снова.» instead of being retitled with this screen's
  fallback. It is NOT re-thrown: re-throwing inside the catch of a floating promise recreates the
  unhandled rejection this step existed to remove, and `grep SessionExpiredError frontend/src`
  shows no redirect or auth-context handler to hand it to — rendering the sentence inline is the
  whole of this codebase's sign-out affordance today (`saveFailureMessages.ts:33`)
- [x] red-frontend (the error banner is announced, not just displayed) — premortem on cc1bc733. The
  load-failure test asserts `findByTestId` + `textContent` and nothing else, so a green satisfying it
  exactly has no reason to add `role="alert"` — and every sibling error surface in the repo carries one
  (`LoginForm.tsx:84`, `LoginForm.tsx:93`, `OAuthErrorBanner.tsx:44`, `VerifyCodeForm.tsx:130`,
  `ExportControl.tsx:139`, `LinkPopover.tsx:140`). Unannounced, the feed simply never populates for an
  assistive-tech user: indistinguishable from an empty account, which is the exact defect this scenario
  exists to kill, unfixed for the users who need it most. Assert via `findByRole('alert')`
- [x] green-frontend (the error banner is announced, not just displayed) — the test reaches the banner
  ONLY by `findByRole('alert')` and asserts `.textContent` on the node the role query returned, so a
  `role` on an empty live region beside the visible sentence does not pass, and a `role` on a wrapper
  containing the cards does not either. Add the role to the element that already carries the message.
  Shipped as one attribute on the existing `<p>`; the `error !== null &&` guard is unchanged
- [S] red-frontend (no live region exists before anything has failed) — **DECIDED BY USER on the
  65294a49 review passes: conditional mounting stands; this pair is skipped and the verification it
  wanted moves outside jsdom.** Three agents converged here. `tdd-rules.md:15-16` settles the
  mechanics — the `error !== null &&` guard is already in production, so the assertion passes against
  HEAD and ZERO production files need modification, which is the definition of `[S]` for both halves.
  What the premortem raised beyond that is not resolvable by any test in this repo: a `role="alert"`
  inserted into the DOM *already containing its text* is the shape assistive tech routinely does not
  announce (the reliable shape is a region already mounted whose content changes), and jsdom returns
  the identical pass either way — there is no axe layer in `frontend/` or `acceptance/` to fail on it.
  The always-mounted-empty region was the alternative and was declined. Original note follows: the
  tempting green the premortem named — dropping the guard so the banner is always mounted — passes ALL
  THREE suites, because nothing in the feature asserts the error surface is ABSENT on a successful
  load. `auth/components/RegisterForm.tsx:65` documents the opposite hazard: an assertive region
  present at first paint announces on load
- [S] green-frontend (no live region exists before anything has failed) — see above; zero production
  files need modification
  (the manual verification this pair traded a test for is NOT a step here — see «Manual Verifications»
  at the end of this file. It is deliberately outside the executable ordering: `workflow.md` selects
  the first `[~]`/`[ ]` as the next work unit, and a step requiring a real screen reader either stalls
  `/continue` or gets fabricated `[x]` by an agent that cannot drive NVDA, which is strictly worse
  than never running it)
- [x] red-frontend (the timeout arm does not paint English on a Russian screen) — RED reproduced from
  scratch rather than trusting the interrupted run's recorded evidence, and it held byte-for-byte:
  `AssertionError: expected 'Request timed out' to be 'Не удалось загрузить проекты'`. No
  `Unable to find`, no 5000ms timeout, no unhandled rejection — the banner mounts and is found
  immediately, so this is the first red in the scenario producing a value-vs-value diff rather than a
  missing element. The rejection is a REAL `RequestTimeoutError`, not an `Error('Request timed out')`
  stand-in: the type is the reason the text survives `send.ts:93`, so imitating the text would test
  nothing. `mockFeedRejection` structurally could not express it, so the harness gained
  `mockFeedFailure(failure: unknown)` — `unknown`, not `Error`, because a bare `HttpError` is an
  object literal (`httpClient.ts:141`) and is not an `Error` at all; `mockFeedRejection` now delegates.
  **`/test-review`'s one proposed fix was DECLINED**: it wanted the sibling's
  `expect(queryAllByTestId('project-card')).toHaveLength(0)` added here, which is the assertion this
  very file already rules vacuous below («a failed load does not also offer the empty state») —
  `items` has one writer, inside `.then`, so zero cards holds on any rejection for every
  implementation. The sibling's copy is a defect with its own remediation step, not a standard to
  spread to a third file; the declension is recorded in-test so a later reader does not re-add it.
  Original note follows: agent-review on
  6a205042. `send.ts:93` re-throws `RequestTimeoutError` with its type intact and
  `httpClient.ts:70-75` builds it as `super('Request timed out')`; `describeFailure`'s last line is
  `error instanceof Error && error.message ? error.message : fallback`, so a timeout takes the
  `.message` branch and paints literally `Request timed out` into `projects-error`.
  `LOAD_FAILURE_FALLBACK` is bypassed on precisely the failure a real user hits most (slow network)
  and honoured on the one that needs a serializer regression
- [x] green-frontend (the timeout arm does not paint English on a Russian screen) — shipped as a
  module-local `describeLoadFailure(failure)` in `ProjectsPage.tsx` holding an
  `OPAQUE_TRANSPORT_FAILURES = [RequestTimeoutError]` list: anything IN the list gets
  `LOAD_FAILURE_FALLBACK`, anything else falls through to `describeFailure` untouched. A positive
  type list rather than "stop preferring `.message` here" precisely so the `SessionExpiredError`
  carve-out below survives by construction — it is not in the list, so it still paints its own
  sentence, and the reason is now a comment beside the list since no assertion guards it yet.
  NOT put in `projectsApi.ts`: the suite declares `vi.mock('../../api/projectsApi')`, so an exported
  helper there is automocked to `undefined` in every feed test — exported constants survive
  automocking, functions do not. The shape generalises for the next step: `HttpError` is an object
  literal and `instanceof` cannot see it, so its arm lands as a sibling predicate inside the same
  function and the call site does not move again. Full frontend suite: 650 passed, 0 failed.
  Original note follows: **BOTH review
  passes on f9d4410f converged on the same trap, so read this before writing the fix.** The RED
  demands that one `Error` subclass with a truthy `.message` paint the fallback instead of its
  message. `SessionExpiredError` is structurally indistinguishable at `send.ts:52`'s predicate, and
  `ProjectsPage.tsx:31-38` documents that the `.message` branch is the ONLY thing delivering
  «Сессия истекла. Войдите снова.» to this screen — which is the app's entire sign-out affordance
  here, since no route redirects on it. So a green phrased as "stop preferring `Error.message` in
  this catch" passes the suite and converts an expired session into a generic feed error with a
  retry that can never succeed. `grep SessionExpired frontend/src/features/projects/` returns the
  production file only: the carve-out lives in a comment, not an assertion. Two further notes:
  (a) fixing this at `send.ts:52` changes user-visible text in `useDocumentInit`, `useGeneration`,
  the ManualEditor save path and the auth forms at once — `describeFailure`'s non-HttpError arm has
  no characterization test anywhere, so nothing would go red; keep the fix inside `ProjectsPage`'s
  catch; (b) the cheapest passing green is a per-type test on `RequestTimeoutError` alone, which the
  5xx arm below then has to extend again — prefer a shape that generalises. The
  `SessionExpiredError` assertion owed by the `red-frontend-api` step below is the named missing
  guard for all of this, and both passes argued it is scheduled one step too late
- [x] red-frontend (the offline user gets English too, and the list cannot reach them) — RED as
  predicted: `AssertionError: expected 'Failed to fetch' to be 'Не удалось загрузить проекты'`.
  Landed as `ProjectsPage.transportFailure.test.tsx`, with two assertions — exact `.textContent`
  equality, plus the `document.body` guard the two sibling screens use.
  **The note below was wrong about one thing and the red corrected it**: the page does NOT catch a
  `TypeError`. A bare `TypeError` matches none of `send.ts`'s carve-outs (no `status`, so
  `isHttpError` is false), falls to `send.ts:96`, and is re-thrown as a plain
  `Error('Failed to fetch')` — the message copied across by `describeFailure`. So this test rejects
  with that plain `Error`, and rejecting with a `TypeError` would have been the UNFAITHFUL stand-in
  here, testing a shape the page can never see. That inverts the sibling's reasoning without
  contradicting it: `timeoutFailure` constructs the real `RequestTimeoutError` precisely because
  `send.ts:93` re-throws THAT one by identity. `/test-review` found nothing to fix and explicitly
  declined two "tightenings" that would have loosened the test — `.trim()` on the textContent
  comparison (the bare form fails on stray whitespace the trimmed form swallows) and `not.toBe` in
  place of `not.toContain` (negated-contains is the stronger of the two).
  Original note follows: **BOTH review
  passes on bcabd515 found this independently, and it is sharper than the timeout it follows.** A
  dropped connection, failed DNS, or offline device does not produce a `RequestTimeoutError` — `fetch`
  rejects with a bare `TypeError('Failed to fetch')` (Firefox: «NetworkError when attempting to fetch
  resource.») long before the 25s `REQUEST_TIMEOUT_MS` deadline. `send.ts:96` flattens it —
  `throw new Error(describeFailure(error, fallback))` — so the type is DESTROYED one layer above the
  page. `describeLoadFailure` therefore cannot ever match it: this is not a missing list entry, it is
  a case `OPAQUE_TRANSPORT_FAILURES` structurally cannot express, while the comment above the list
  reads as though the transport class is closed. And it is the commit's own justification undone —
  «the failure a real user hits most (slow network)» is a `TypeError` far more often than a 25s
  timeout. The guard exists on two other screens and was not carried across:
  `LoginForm.networkError.test.tsx:80` and `ExportControl.error.test.tsx:101` both assert
  `.not.toContain('Failed to fetch')`. One `mockFeedFailure(new Error('Failed to fetch'))` case.
  Expect it RED, and note it cannot go green by extending the list — the green here inverts the
  design to an allow-list of Russian-bearing types, or accepts the `send.ts` change bcabd515 declined
- [x] green-frontend (the offline user gets English too, and the list cannot reach them) — shipped as
  option (a): `describeLoadFailure` is now an ALLOW-list, entirely inside `ProjectsPage`'s catch;
  `send.ts` untouched, `OPAQUE_TRANSPORT_FAILURES` and the `RequestTimeoutError` import are gone.
  The inversion changes the question from «which failures are opaque?» (an open set the transport
  keeps growing — the red proved it cannot even be enumerated once `send.ts:96` flattens the type)
  to «whose text is this, and is it already addressed to this user?», which is closed at three
  authors. **The premortem's hazard is why it is not a type allow-list**: two of the three authors
  are invisible to `instanceof`. A 4xx/5xx arrives as a bare `HttpError` OBJECT LITERAL
  (`httpClient.ts:141`) and is matched with `isHttpError`, preserving both the server's Russian
  `detail` and the bodyless-5xx `(HTTP 500)` suffix; `SessionExpiredError` IS a real type
  (`send.ts:62` re-throws by identity) and both arms route to `describeFailure` unchanged, so
  «Сессия истекла. Войдите снова.» survives by construction — still guarded by comment only, the
  assertion is still owed by the `red-frontend-api (the two arms this commit was designed around)`
  step below. **The third author was the real design constraint and neither review pass named it**:
  this feature's own `MISSING_UPDATED_AT_MESSAGE` reaches the catch as a plain `Error`, exactly the
  shape `Failed to fetch` arrives in — same type, same truthiness, nothing to tell them apart but
  the string. So a type-only allow-list of ANY composition turns `ProjectsPage.loadFailure.test.tsx`
  red. It is matched by message identity against a module-local `FEED_AUTHORED_MESSAGES` list
  holding the exported constant. That list is the one maintenance cost accepted here, and it fails
  in the SAFE direction: a contract guard added later and not listed degrades to the generic Russian
  sentence — a lost diagnostic, never an English leak. The nine-required-fields step below inherits
  it and should decide the guard's shape and this list's shape together. A Cyrillic-detection
  heuristic was considered as the self-maintaining alternative and rejected: it makes the screen's
  copy rules depend on a regex over server-controlled text. Both assertions pass, including the
  `document.body` guard that never executed in the red. Full frontend suite: 651 passed, 0 failed,
  3 skipped (174 files passed, 1 skipped); `tsc --noEmit` clean. Original note follows: the red
  confirmed this cannot go green by extending `OPAQUE_TRANSPORT_FAILURES`: there is no surviving type
  to list, the flattening happened a layer above. Two live options — (a) invert `describeLoadFailure`
  to an ALLOW-list of types whose message is Russian-bearing, on which `SessionExpiredError` must
  stay (its «Сессия истекла. Войдите снова.» is this codebase's whole sign-out affordance here), or
  (b) the `send.ts` change bcabd515 declined, whose cost is unchanged: four features share that line
  and its non-HttpError arm has no characterization test. The second assertion (`document.body` must
  not contain `Failed to fetch`) never executed in the red — it has to hold too
- [x] red-frontend-api (a 200 with no `items` renders a JS engine message to the user) — RED exactly
  as predicted, and the run makes the leak concrete:
  `AssertionError: expected TypeError { message: "Cannot read properties of undefined (reading
  'map')" } to deeply equal Error { message: "Сервер вернул некорректный список проектов." }`.
  Landed as `projectsApi.pageShape.test.ts` (a sibling of `projectsApi.wireContract.test.ts`, this
  feature's split convention), one `it.skip`, stubbing the literal `{}` that `httpClient.ts:167`
  produces for a 204 / empty 200 / unparseable body — not a hypothetical shape. It reuses the
  sibling's capture-the-settlement helper so the assertion pins outcome, error TYPE and message
  together: `.rejects.toThrow()` would pass on the `TypeError` itself.
  **The green owes TWO changes, and the second is the one that is easy to miss**: (1) export the
  message constant from `projectsApi.ts` — the test holds `EXPECTED_MESSAGE` locally only because
  RED may not touch production, and the `/refactor` after green replaces the literal with the import
  or the two definitions drift, same sequence `MISSING_UPDATED_AT_MESSAGE` went through; (2) add
  that constant to `FEED_AUTHORED_MESSAGES` in `api/loadFailureMessages.ts`. Since 7baba471 the page
  renders a plain `Error`'s message ONLY if it is on that allow-list, so a guard that rejects
  correctly but is not listed degrades to the generic `LOAD_FAILURE_FALLBACK` — fails in the safe
  direction (no English leak) but this sentence never reaches the screen and step (1) buys nothing.
  Do NOT resolve `items: []` instead: that makes a broken endpoint render identically to a user
  with no projects, the exact confusion this scenario exists to kill, and 2.3's empty state would
  then invite the user to create a first project on top of a server fault. Full frontend suite:
  651 passed, 0 failed, 4 skipped (174 files passed, 2 skipped); `tsc --noEmit` clean.
  Original note follows: agent-review
  on bcabd515. `projectsApi.ts:96` does `data.items.map(...)` with no shape check, and
  `httpClient.ts:167` deliberately turns an empty or unparseable SUCCESSFUL body into `{}`
  (`await res.json().catch(() => ({}))`). A 204, an empty 200, or any body missing `items` therefore
  throws `TypeError` INSIDE `listProjects` — downstream of `send`, so it reaches the catch as a real
  `Error` and the banner paints `Cannot read properties of undefined (reading 'map')`. English, and
  an internal engine string, on the Russian screen. The file's own fail-closed `parseUpdatedAt`
  contract exists to stop exactly this class of serializer breakage from looking deliberate — it
  guards a field of an item but not the presence of `items`, so the weaker input gets the worse
  rendering. Pair with the shaping decision the deferred nine-required-fields step below owes
- [~] green-frontend-api (a 200 with no `items` renders a JS engine message to the user)
- [ ] red-frontend (a 4xx's server-authored Russian explanation reaches the user) — **BOTH review
  passes on 7baba471, and it is a regression that commit introduced rather than an inherited gap.**
  `send.ts` re-throws raw only for `RequestTimeoutError` and `isHttpError(error) && error.status >= 500`;
  every 4xx falls to `throw new Error(describeFailure(error, fallback))`, so it arrives at the page as a
  plain `Error` whose `.message` is ALREADY the server's Russian `detail`. In the new three-arm
  `describeLoadFailure` that plain `Error` matches neither `isHttpError` nor `SessionExpiredError` nor
  `FEED_AUTHORED_MESSAGES`, and lands on `LOAD_FAILURE_FALLBACK`. Before 7baba471 it rendered. A 403
  «Проект принадлежит другому пользователю» is now the generic sentence with a retry that can never
  succeed — and both the commit message and the `isHttpError` arm's comment assert this arm keeps the
  4xx detail, which is true of the 5xx half only. The comment is authoritative in tone and a maintainer
  will trust it over tracing `send.ts`: the narration is part of the defect. The design question this
  step must actually settle, and which 7baba471 resolved silently: at this screen a flattened 4xx and a
  flattened transport failure are the SAME SHAPE (plain `Error`, truthy Russian-or-English `.message`),
  so an assertion that a 4xx detail renders collides head-on with the transport test enabled in that
  same commit. Whatever distinguishes them cannot be the type
- [ ] green-frontend (a 4xx's server-authored Russian explanation reaches the user)
- [ ] red-frontend (an English 5xx body does not reach the Russian screen) — premortem on 7baba471, the
  leak that survives the arm added to stop leaks. `describeFailure` returns `detail` verbatim for any
  5xx that is not `error_code === 'INTERNAL_ERROR'` (`send.ts`, deliberately: a 5xx that EXPLAINS itself
  keeps its text). Correct for autosave; on this Russian-only feed «Upstream provider quota exceeded»
  paints in English through the `isHttpError` arm. The `document.body` non-disclosure assertion added in
  31933cd4 is bound to the literal `'Failed to fetch'` and cannot see it. Reject with
  `{status: 503, body: {detail: '<English>'}}`; decide here whether this screen accepts server 5xx prose
  at all
- [ ] green-frontend (an English 5xx body does not reach the Russian screen)
- [ ] refactor (`FEED_AUTHORED_MESSAGES` cannot be under-filled) — agent-review on 7baba471. The list is
  hand-maintained and its failure mode is silent: omitting a guard message produces no type error, no
  test failure, no runtime signal, just a lost diagnostic. The `green-frontend-api` step directly above
  adds the second entry, so the first chance to lose one is the very next work unit. Have `projectsApi.ts`
  export its guard messages as one frozen array and let `loadFailureMessages.ts` consume THAT rather than
  re-listing members — omission becomes structurally impossible instead of a review duty
- [ ] red-frontend-api (`send` re-throws `RequestTimeoutError` with its type intact) — premortem on
  bcabd515: the fix is load-bearing on a contract NOTHING tests. The timeout test declares
  `vi.mock('../../api/projectsApi')`, so `send.ts` never executes in that suite — the real type is
  injected at the mock boundary, ABOVE the layer carrying the contract. `shared/api/__tests__/` has
  `httpClient.timeout.test.ts` (constructs the error) and `send.internalErrorFallback.test.ts` (the
  500 arm); neither asserts the re-throw preserves identity. Flatten that branch to
  `throw new Error(describeFailure(...))` and all 650 tests stay green while production regresses to
  English. `await expect(send(...)).rejects.toBeInstanceOf(RequestTimeoutError)` on a timing-out
  transport. NOTE: this one lives in `shared/api/`, not in the projects feature
- [ ] green-frontend-api (`send` re-throws `RequestTimeoutError` with its type intact)
- [ ] red-frontend-api (the two arms this commit was designed around are asserted) — premortem on
  6a205042, and the sharpest of the round: the ONLY rejection any test exercises is a plain
  `new Error(...)`, which is the single branch where `describeFailure` and the `e.message` the step
  note asked for are indistinguishable. So the whole deliberate divergence — the reason for 26 lines
  of commit message and 12 of in-file comment — is invisible to the suite, and a later refactor
  toward the 4.2 retry affordance reintroduces both defects green. Two arms owed: `SessionExpiredError`
  asserting «Сессия истекла. Войдите снова.» (NOT the screen fallback), and a bare 5xx `HttpError`
  **object literal** (`httpClient.ts:141`, not an `Error`) asserting `Не удалось загрузить проекты
  (HTTP 500)` and explicitly not containing `undefined`. `mockFeedRejection` wraps its argument in
  `new Error` and structurally cannot express either — widen the harness first
- [ ] green-frontend-api (the two arms this commit was designed around are asserted)
- [ ] red-frontend (a pending load is not an empty account) — premortem on 6a205042, blast radius 100%
  of loads rather than the failure minority. `ProjectsPage` models two states (`items`, `error`) where
  the load has three: `useState<ProjectSummary[]>([])` makes pending and empty-resolved literally the
  same value, and `error === null` holds during pending exactly as on success. Harmless-looking while
  the in-flight window is visually blank; the moment 2.3 lands the empty-state affordance, every user
  on a slow connection reads «у вас пока нет проектов» before their projects arrive — this scenario's
  own defect, reintroduced on the pending path. `feedTestHarness` has no `mockFeedPending`, so the
  state is not merely untested, it is not expressible: render against `new Promise(() => {})`.

  **RE-SPECIFIED after agent-review on 9f8c652a**, which caught this note repeating the defect that
  generated it. The original text asked to assert the empty-state affordance ABSENT — but that
  affordance is scenario 2.3 and does not exist in `ProjectsPage.tsx` today, so the assertion has zero
  writers and holds for every implementation forever: verbatim the vacuous-assertion finding that
  produced the `a failed load does not also offer the empty state` step above. Assert instead that a
  pending affordance is PRESENT (which is falsifiable today, and is what 4.1's skeleton wants
  anyway); the error-surface-absent half stays as written. Defer the empty-state-absent half to 2.3
- [x] refactor (the RED evidence in this feature cannot discriminate) — **pulled ahead of the four
  remaining reds and done, on agent-review's ordering argument: repairing the measuring instrument
  after every remaining measurement is worth nothing.** Fixed by RAISING `testTimeout` to 10000 in
  `vite.config.ts`, not by lowering `asyncUtilTimeout` — that 5000 is a measured chunk-load budget
  (see `setup.ts`) and cutting it trades unreadable failures for flaky ones. Verified by breaking a
  query on purpose: the run now prints `TestingLibraryElementError: Unable to find role="marquee"`
  with the full rendered-DOM dump where it previously printed only `Test timed out in 5000ms`. The
  two `describe` titles were disambiguated in the same pass — `ProjectsPage announces a rejected load
  to assistive technology` vs `ProjectsPage shows a rejected load instead of an empty feed`. Original
  note follows: agent-review on 9f8c652a,
  systemic rather than one file. `src/test/setup.ts` sets `asyncUtilTimeout: 5000`, exactly vitest's
  default `testTimeout`, so on every missing-element red the OUTER timeout wins the race and Testing
  Library's «Unable to find role/testid» message with its DOM dump is never printed. Every red in this
  scenario therefore recorded the same evidence — `Test timed out in 5000ms` — which is identical
  output for the real defect, for `vi.mock` failing to apply, and for the component rendering nothing
  at all. Every prediction/actual match in this scenario's history is weaker than it reads. Drop
  `asyncUtilTimeout` below `testTimeout` so the DOM dump survives; while there, disambiguate the two
  near-identical `describe` titles (`ProjectsPage error surface when listProjects rejects` vs
  `ProjectsPage when listProjects rejects`) that a CI log cannot tell apart
- [ ] green-frontend (a pending load is not an empty account)
- [ ] align-design (the failure is styled as a failure, not as helper text) — BOTH review passes on
  6a205042 raised this independently. `.projects-error` uses `var(--text-muted)`, the same token
  `.project-card-date` uses for a de-emphasised timestamp — no background, no border, no icon. The
  direct analogue is `HistoryPage.css:86-93`, also a page-level load-failure banner:
  `background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); color: var(--error)`. On an
  otherwise blank page one line of grey text reads as an empty state. The DOM now tells broken from
  empty; the pixels barely do. No jsdom surface — this is a styling review item, which is why it is an
  `align-design` step and not a red/green pair
- [ ] refactor (`error` gains a writer that clears it) — agent-review on 6a205042. `setError` is called
  in exactly one place and never reset. Guarded by construction today (deps are `[]`, one load per
  mount), so no test is owed and none would fail. It stops being guarded at the first scenario giving
  the effect a dependency — 2.x/3.x add `q`/`sort`/`page`, already anticipated by the `_params` comment
  in `projectsApi.ts`, and 4.2 adds explicit retry. At that point a failed load followed by a
  successful one renders a fresh feed under a stale banner: a page claiming both that it broke and
  that here are your projects. Three lines now, a bug found by 4.2 otherwise
- [ ] red-frontend (a failed load does not also offer the empty state) — agent-review on cc1bc733:
  `expect(queryAllByTestId('project-card')).toHaveLength(0)` cannot fail. `useState([])` has exactly one
  writer, inside `.then`; on a rejection it never runs, so zero cards holds for every implementation,
  before and after green. The claim the commit actually intends is untested — «у вас пока нет проектов»
  lives only in prose today, so the moment 2.3 lands the empty state, a page rendering BOTH the error
  and the empty-state invitation passes the current test with the precise confusion it was written to
  eliminate. Pin the empty-state affordance ABSENT on the error path; ordering against 2.3 is the open
  question, not whether the assertion is owed
- [ ] green-frontend (a failed load does not also offer the empty state)
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

## Manual Verifications

Not work units. `workflow.md` selects the first `[~]`/`[ ]` entry above as the next unit to
dispatch; these require a human at a real machine, so they live outside that ordering — a manual
step inside it either stalls `/continue` or gets a fabricated `[x]` from an agent that cannot
perform it, which is worse than never running it. **A story must not move to the Done table in
`stories.md` while any box here is unticked.**

- [ ] The failed-load banner on «Мои проекты» is actually announced (scenario 1.1) — drive the feed
  to a failed load with a real screen reader (NVDA or VoiceOver) and confirm the sentence is spoken.
  This is the guard the `[S]` live-region pair traded a test for. `role="alert"` inserted into the
  DOM *already containing its text* is the shape assistive tech routinely does not announce; the
  reliable shape is a region already mounted whose content changes. jsdom returns the identical pass
  either way, and there is no axe layer in `frontend/` or `acceptance/` to fail on it. If it is NOT
  announced, the fix is the always-mounted-empty region and the conditional-mounting decision
  recorded on the `[S]` pair is reopened.
