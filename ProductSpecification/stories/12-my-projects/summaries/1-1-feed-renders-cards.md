# Scenario 1.1: The feed renders the user's work as cards — Journey Summary

## green-frontend (2026-08-04)

**Decision:** A plausible card date is the fixed range 1900..2200; neither bound is derived from `new Date()`.
**Why:** A ceiling of `new Date().getFullYear()` passes every test and blanks the date on a project the user just edited whenever the client clock trails the server, and on every 31 December evening.
**Where applied:** `EARLIEST_PLAUSIBLE_YEAR` / `LATEST_PLAUSIBLE_YEAR` in `frontend/src/features/projects/formatCardDate.ts`.

## green-frontend (2026-08-04)

**Quirk:** The floor must sit strictly below 1970, not at it.
**Where:** `formatCardDate.ts`, against `EPOCH_DATE_PROJECT` in `projectFixtures.ts`.
**Implication:** `1970-01-01T00:00:00Z` reads `getFullYear() === 1969` in any negative-offset timezone, so a bound of `year >= 1970` blanks the epoch date the sibling suite pins as genuinely renderable.

## green-frontend-api (2026-08-04)

**Decision:** A required wire field absent makes `listProjects` reject the whole page with an exported message constant, rather than dropping the row or mapping `undefined`.
**Why:** A serializer that omits a required field on one item is broken for all of them, and a silently short page hides that as well as an em dash does; mirrors `parseVersion` / `INVALID_VERSION_MESSAGE` in `generation/api/documentApi.ts`.
**Where applied:** `parseUpdatedAt` + `MISSING_UPDATED_AT_MESSAGE` in `frontend/src/features/projects/api/projectsApi.ts`.

## green-frontend-api (2026-08-04)

**Surprise:** Importing the production message constant into the test made a copy edit stop reddening it.
**Why:** Mutation-checked — disabling the guard and swapping in `send`'s transport fallback both still fail, but editing the message in `projectsApi.ts` now passes, because both sides read one definition.
**Impact:** Fail-closed suites pin *which* guard fired, not the exact Russian wording; wording changes need review, not a unit test.

## green-frontend-api (2026-08-04)

**Quirk:** `ProjectsPage.tsx` consumes `listProjects().then(...)` with no `.catch` and no error state.
**Where:** `frontend/src/features/projects/components/ProjectsPage.tsx`.
**Implication:** Any rejection the api layer adds renders an unhandled promise rejection plus a page visually identical to «у вас пока нет проектов» — quieter than the failure it replaced.

## red-frontend-api (2026-08-04)

**Quirk:** `npm run lint` cannot run on this branch — oxlint dies with `MODULE_NOT_FOUND` loading `node_modules/oxlint/dist/bindings.js`.
**Where:** frontend toolchain, reproducible with all story changes stashed.
**Implication:** The lint gate is unverifiable for every commit here; `tsc --noEmit` and `prettier --check` are the only static gates that actually ran.
