# Story 14: Analytics Event Tracking — Frontend Progress

Owns: Frontend Scenarios (`02_UI_Tests.md`). Narrative/decisions/Spec checklist live in
`progress.md`; Backend/Integration/Security/Load/Infrastructure in `progress-backend.md`.
`ProductSpecification/stories.md` is the cross-file rollup. Extended scenarios
(`tests/extended/02_UI_Tests_Extended.md`) are folded in once the critical file is green.

This story adds **no new UI surface** — it instruments the screens that already exist.
`align-design` is therefore `[S]` on every scenario unless one turns out to need a visible
control, in which case: stop and report before adding it (see `progress.md` § Governing
principle).

## Frontend Scenarios (02_UI_Tests.md)

### 1.1 A first-ever visitor is given an identity before anything is reported
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [ ] green-selenium
- [ ] demo

### 1.2 A returning visitor keeps the identity it already had
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [ ] green-selenium
- [ ] demo

### 1.3 A stored identity that is not well-formed is replaced, not reused
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [ ] green-selenium
- [ ] demo

### 1.4 Signing in does not change the visitor identity
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [ ] green-selenium
- [ ] demo

### 2.1 The first visit carrying campaign parameters freezes them
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [ ] green-selenium
- [ ] demo

### 2.2 A later visit from a different campaign does not overwrite the first
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [ ] green-selenium
- [ ] demo

### 2.3 A visit with no campaign parameters leaves the browser open to a later first touch
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [ ] green-selenium
- [ ] demo

### 2.4 Registration carries the frozen set, not the current address
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [ ] green-selenium
- [ ] demo

### 2.5 Multibyte campaign parameters survive the freeze unchanged
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [ ] green-selenium
- [ ] demo

### 3.1 One page load reports exactly one site visit
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [ ] green-selenium
- [ ] demo

### 3.2 Reaching the registration screen reports it once
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [ ] green-selenium
- [ ] demo

### 3.3 Opening a document in the editor reports it once
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [ ] green-selenium
- [ ] demo

### 3.4 Opening a document twice in one gesture reports one opening
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [ ] green-selenium
- [ ] demo

### 3.5 Moving within the site reports no further site visit
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [ ] green-selenium
- [ ] demo

### 3.6 Two reports on the wire together keep their dispatch order
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [ ] green-selenium
- [ ] demo

### 4.1 A browser that cannot store still reports, and says so in the data
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [ ] green-selenium
- [ ] demo

### 4.2 Two loads from a browser that cannot store are two different visitors
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [ ] green-selenium
- [ ] demo

### 4.3 An unreachable analytics endpoint is invisible to the visitor
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [ ] green-selenium
- [ ] demo

### 4.4 A visitor who leaves immediately is still counted
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [ ] green-selenium
- [ ] demo

### 4.5 An analytics endpoint that never answers blocks nothing
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [ ] green-selenium
- [ ] demo

### 4.6 Every refusal from the analytics endpoint is inert in the browser
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [ ] green-selenium
- [ ] demo

### 4.7 Each send-failure family is counted, and a success is not
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [ ] green-selenium
- [ ] demo

### 5.1 Deleting the account clears the identity and the frozen attribution
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [ ] green-selenium
- [ ] demo

### 5.2 Deleting the account leaves the visitor's other preferences alone
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [ ] green-selenium
- [ ] demo

### 5.3 A registration after a deletion is not attributed to the deleted account's campaign
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [S] align-design (no new UI surface — see header)
- [ ] green-selenium
- [ ] demo

