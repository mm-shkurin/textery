# Task 6: Backfill TDD coverage for the OAuth sign-in slice (Story 16) -- Progress

Type: refactoring

## Spec
- [x] spec

## Fix

Each step: run `/test-coverage` on the layer first to locate genuine gaps, then add only the
missing red/green coverage. Behavior must not change. Confirm an already-covered layer and
move on rather than rewriting existing tests. Steps are filled in as Story 16 lands its
reduced scenarios — a scenario committed under reduced-TDD gets its backfill row here the
same day.

### Step 1: Ceremony backfill for the scenarios shipped reduced
- [ ] restore the per-step red/green record for every `[S] reduced-TDD` entry in
      `stories/16-oauth-signin/progress-backend.md`
- [ ] `/test-review` over the OAuth acceptance + usecase tests (strict assertions on parsed
      fields, no `contains` / `isNotNull` looseness)
- [ ] `/test-coverage` per layer: usecase, rest, db, oauth provider adapter
- [ ] `/refactor` pass over the OAuth slice, landing in its own commit
- [ ] `/agent-review` + `/premortem` fresh-context passes

### Step 2: Deferred scenarios (red-first, full cycle)
- [ ] 2.6 A code minted on one instance is redeemable on another
- [ ] 3.2 Concurrent first sign-ins for one identity create one account
- [ ] 3.3 Email case / normalization / locale variance resolves to one account
- [ ] 3.4 A code that yields no session is not burned
- [ ] 3.5 Extra request fields cannot over-bind on auto-create
- [ ] 3.6 Sign-in failure copy does not reveal account existence
- [ ] 3.7 A large provider subject id is not truncated
- [ ] 3.9 A failed session issue leaves no orphan account
- [ ] 3.10 Recovery after a lost exchange response

### Step 3: VK ID
- [ ] carry VK end to end once credentials exist, or record it as unconfigured with its
      named error under test
