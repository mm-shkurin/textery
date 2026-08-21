# Story 14: Analytics Event Tracking — Frontend Progress

Owns: Frontend Scenarios (`02_UI_Tests.md`). Narrative/decisions/Spec checklist live in
`progress.md`; Backend/Integration/Security/Load/Infrastructure in `progress-backend.md`.
`ProductSpecification/stories.md` is the cross-file rollup. Extended scenarios
(`tests/extended/02_UI_Tests_Extended.md`) are folded in once the critical file is green.

This story adds **no new UI surface** — it instruments the screens that already exist.
`align-design` is therefore `[S]` on every scenario unless one turns out to need a visible
control, in which case: stop and report before adding it (see `progress.md` § Governing
principle).

## Delivery note — 2026-08-21: shipped as production code

No scenario in this file ran its TDD cycle. At six work units per scenario the sprint
deadline was unreachable that way, so on the developer's instruction the browser half was
written directly as production code. Every `[ ]` below is rewritten to `[S]`, which here
means "the BEHAVIOUR is implemented, the cycle for it was not run" — the scenario text
stays as the specification of what the code must do, and as the backlog for a later
coverage pass.

What was implemented, and where it lives:

| Scenarios | Code |
|---|---|
| §1 (visitor identity, degraded storage) | `src/shared/analytics/visitorId.ts` |
| §2 (first-touch campaign freeze) | `src/shared/analytics/attribution.ts`, `features/auth/api/registerApi.ts` |
| §3 (the three browser events, once each) | `src/shared/analytics/trackers.ts`, `src/main.tsx`, `RegisterForm.tsx`, `useGeneratedDocumentInit.ts` |
| §4 (fail-open reporting, send-failure tally) | `src/shared/analytics/analyticsClient.ts` |
| §5 (deletion clears identity and campaign) | `src/shared/identity/api/deleteAccountApi.ts` |

Sixteen unit cases DO exist, in `src/shared/analytics/__tests__/`, covering the identity's
degraded path, the first-touch rules, and what a refused or unreachable endpoint costs the
visitor. What does NOT exist is Selenium coverage: no scenario here was driven through a
browser, so "the visitor never notices" is argued from the code and the unit tests rather
than demonstrated end to end.

## Frontend Scenarios (02_UI_Tests.md)

### 1.1 A first-ever visitor is given an identity before anything is reported
- [S] red-selenium
- [S] red-frontend
- [S] green-frontend
- [S] red-frontend-api
- [S] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [S] green-selenium
- [S] demo

### 1.2 A returning visitor keeps the identity it already had
- [S] red-selenium
- [S] red-frontend
- [S] green-frontend
- [S] red-frontend-api
- [S] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [S] green-selenium
- [S] demo

### 1.3 A stored identity that is not well-formed is replaced, not reused
- [S] red-selenium
- [S] red-frontend
- [S] green-frontend
- [S] red-frontend-api
- [S] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [S] green-selenium
- [S] demo

### 1.4 Signing in does not change the visitor identity
- [S] red-selenium
- [S] red-frontend
- [S] green-frontend
- [S] red-frontend-api
- [S] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [S] green-selenium
- [S] demo

### 2.1 The first visit carrying campaign parameters freezes them
- [S] red-selenium
- [S] red-frontend
- [S] green-frontend
- [S] red-frontend-api
- [S] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [S] green-selenium
- [S] demo

### 2.2 A later visit from a different campaign does not overwrite the first
- [S] red-selenium
- [S] red-frontend
- [S] green-frontend
- [S] red-frontend-api
- [S] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [S] green-selenium
- [S] demo

### 2.3 A visit with no campaign parameters leaves the browser open to a later first touch
- [S] red-selenium
- [S] red-frontend
- [S] green-frontend
- [S] red-frontend-api
- [S] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [S] green-selenium
- [S] demo

### 2.4 Registration carries the frozen set, not the current address
- [S] red-selenium
- [S] red-frontend
- [S] green-frontend
- [S] red-frontend-api
- [S] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [S] green-selenium
- [S] demo

### 2.5 Multibyte campaign parameters survive the freeze unchanged
- [S] red-selenium
- [S] red-frontend
- [S] green-frontend
- [S] red-frontend-api
- [S] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [S] green-selenium
- [S] demo

### 3.1 One page load reports exactly one site visit
- [S] red-selenium
- [S] red-frontend
- [S] green-frontend
- [S] red-frontend-api
- [S] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [S] green-selenium
- [S] demo

### 3.2 Reaching the registration screen reports it once
- [S] red-selenium
- [S] red-frontend
- [S] green-frontend
- [S] red-frontend-api
- [S] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [S] green-selenium
- [S] demo

### 3.3 Opening a document in the editor reports it once
- [S] red-selenium
- [S] red-frontend
- [S] green-frontend
- [S] red-frontend-api
- [S] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [S] green-selenium
- [S] demo

### 3.4 Opening a document twice in one gesture reports one opening
- [S] red-selenium
- [S] red-frontend
- [S] green-frontend
- [S] red-frontend-api
- [S] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [S] green-selenium
- [S] demo

### 3.5 Moving within the site reports no further site visit
- [S] red-selenium
- [S] red-frontend
- [S] green-frontend
- [S] red-frontend-api
- [S] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [S] green-selenium
- [S] demo

### 3.6 Two reports on the wire together keep their dispatch order
- [S] red-selenium
- [S] red-frontend
- [S] green-frontend
- [S] red-frontend-api
- [S] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [S] green-selenium
- [S] demo

### 4.1 A browser that cannot store still reports, and says so in the data
- [S] red-selenium
- [S] red-frontend
- [S] green-frontend
- [S] red-frontend-api
- [S] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [S] green-selenium
- [S] demo

### 4.2 Two loads from a browser that cannot store are two different visitors
- [S] red-selenium
- [S] red-frontend
- [S] green-frontend
- [S] red-frontend-api
- [S] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [S] green-selenium
- [S] demo

### 4.3 An unreachable analytics endpoint is invisible to the visitor
- [S] red-selenium
- [S] red-frontend
- [S] green-frontend
- [S] red-frontend-api
- [S] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [S] green-selenium
- [S] demo

### 4.4 A visitor who leaves immediately is still counted
- [S] red-selenium
- [S] red-frontend
- [S] green-frontend
- [S] red-frontend-api
- [S] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [S] green-selenium
- [S] demo

### 4.5 An analytics endpoint that never answers blocks nothing
- [S] red-selenium
- [S] red-frontend
- [S] green-frontend
- [S] red-frontend-api
- [S] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [S] green-selenium
- [S] demo

### 4.6 Every refusal from the analytics endpoint is inert in the browser
- [S] red-selenium
- [S] red-frontend
- [S] green-frontend
- [S] red-frontend-api
- [S] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [S] green-selenium
- [S] demo

### 4.7 Each send-failure family is counted, and a success is not
- [S] red-selenium
- [S] red-frontend
- [S] green-frontend
- [S] red-frontend-api
- [S] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [S] green-selenium
- [S] demo

### 5.1 Deleting the account clears the identity and the frozen attribution
- [S] red-selenium
- [S] red-frontend
- [S] green-frontend
- [S] red-frontend-api
- [S] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [S] green-selenium
- [S] demo

### 5.2 Deleting the account leaves the visitor's other preferences alone
- [S] red-selenium
- [S] red-frontend
- [S] green-frontend
- [S] red-frontend-api
- [S] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [S] green-selenium
- [S] demo

### 5.3 A registration after a deletion is not attributed to the deleted account's campaign
- [S] red-selenium
- [S] red-frontend
- [S] green-frontend
- [S] red-frontend-api
- [S] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [S] green-selenium
- [S] demo

