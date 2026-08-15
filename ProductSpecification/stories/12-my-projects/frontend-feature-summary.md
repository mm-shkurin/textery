# Story 12 «Мои проекты» — Frontend, what actually works today

Written by the frontend session. Scope: `frontend/src/features/projects/`. This is a
**capability** summary — what the screen can and cannot do — not a checklist. The step-by-step
state lives in `progress-frontend.md`; this file answers "what would a user see if we shipped
now".

**Backend status: `GET /api/v1/projects` does not exist.** Every capability below is built and
tested against a mock of that endpoint. Nothing here has ever made a live call, and no Selenium
leg has run — those are batched for a full-stack pass once the endpoint lands.

Scenario coverage: **1 of 25 in flight** (1.1, «The feed renders the user's work as cards»).
Scenarios 1.2–6.5 are untouched. Suite: 652 passing, 3 skipped.

---

## 1. Reading the feed

`listProjects()` (`api/projectsApi.ts`) fetches the feed page, authenticates from the stored
session, and maps the wire body to view models. The card grid renders from it on mount, one load
per mount, no parameters yet — search, sort and paging (scenarios 2.x/3.x) are not wired, though
the mapper already carries the `_params` seam for them.

## 2. Rendering a project card

`ProjectCard.tsx` + `ProjectFolderIcon.tsx` render title, document-type badge, a coloured accent
per type, and the last-modified date. The card reads `updatedAt`, never `createdAt`, and that
distinction is pinned by a test rather than left to fixtures that happen to set both equal. An
unrecognised document type from the server still renders — it takes a blue fallback accent
instead of blanking the card.

## 3. Dates the user can trust

`formatCardDate.ts` is the most heavily guarded piece of this feature, because the date is the
one field a broken backend can make *look* fine.

- Current-year dates show day + month; older ones append the year.
- A missing, null, numeric, or unparseable timestamp renders `—`, never `Invalid Date NaN` and
  never `1 января 1970`. The epoch is treated as a real date, because it is one — the guard is on
  the input's shape, not on the value.
- Backend null-sentinels (`0001-01-01`, `9999-12-31`, Postgres `±infinity`) are rejected by a
  bounded plausible-year window (1900–2200). The ceiling is a fixed constant, deliberately not the
  client's clock: a clock-anchored bound would blank the date on work the user just edited
  whenever their clock trails the server, and on every 31 December evening.

## 4. Failure that reads as failure

This is where most of the work went, and it is worth stating plainly: **a load that fails must not
look like an account with no projects.** Those two states are visually identical unless something
forces them apart.

- A rejected load renders an error banner and zero cards. The page no longer leaves an unhandled
  promise rejection behind.
- The banner carries `role="alert"`, matching every other error surface in the app. Whether a
  screen reader *actually announces* it is an open manual verification (see the bottom of
  `progress-frontend.md`) — jsdom cannot answer that question and this repo has no axe layer.
- **The screen speaks Russian on every failure path we have closed.** A 25-second timeout and a
  dropped connection / failed DNS both used to paint raw English (`Request timed out`,
  `Failed to fetch`) onto a Russian-only screen; both now show «Не удалось загрузить проекты».
  These needed two different fixes, because a timeout keeps its type across the transport layer
  and a dropped connection does not — `send.ts` flattens the latter into a plain `Error` one layer
  above the page, so no type-based rule can ever see it.
- The routing rule that resulted (`api/loadFailureMessages.ts`) selects by **who authored the
  text**, not by error type: an expired session keeps its own «Сессия истекла. Войдите снова.»
  sentence — this screen's entire sign-out affordance, since no route redirects on it — this
  feature's own guard messages render verbatim, and everything else degrades to the generic
  Russian sentence. Failure direction is deliberate: a lost diagnostic, never an English leak.

## 5. Refusing a broken contract instead of rendering it

`listProjects` fails closed rather than passing suspicious data to the UI, on the principle that a
serializer which breaks one field is broken for all of them — and a silently short page hides that
as well as a blank date does.

- An item missing `updated_at` rejects the whole page with a named Russian message.
- A success response whose `items` is not an array rejects the same way, instead of throwing
  `Cannot read properties of undefined (reading 'map')` at the user.

## What is NOT built

- Search, sort, paging, the list (row) view, «Недавние проекты», the empty state, the loading
  skeleton, retry, repeat-a-failed-generation, opening a card into the editor, and view
  persistence. All of scenarios 1.2 through 6.5.
- A pending load is currently indistinguishable from an empty account in the component's state
  model — harmless while the empty state does not exist, and a queued step before it does.
- The error banner is styled as muted helper text, not as a failure. On an otherwise blank page it
  still *reads* like an empty state even though the DOM now tells them apart.

## Known defects, already recorded as steps

Ordered by how visible they would be in production:

1. **A 4xx's server-authored Russian explanation is dropped** and replaced with the generic
   sentence — a regression introduced by the failure-routing change, since `send.ts` flattens
   every 4xx into a plain `Error` that the new rule does not recognise. A user who cannot ever
   succeed is offered a retry.
2. **The page-shape guard reads `.items` off a value it never validated** — a 200 whose body is
   literal `null` still throws an engine `TypeError`, which then reads to the user as a network
   problem rather than a server-shape fault.
3. **An English 5xx `detail` still reaches the screen** through the one arm that passes server
   text through untouched.
4. Several contracts the feature depends on are asserted nowhere: the expired-session sentence,
   the `HttpError` arm, and `send.ts`'s type-preserving re-throw.
5. `История`'s own date formatter renders the epoch as `1 января 1970` — the same defect this
   story found, live on a screen this story has not touched.
