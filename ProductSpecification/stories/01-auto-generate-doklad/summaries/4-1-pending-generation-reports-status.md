# Scenario 4.1: A pending generation reports its status without document content — Journey Summary

## green-usecase (2026-07-10)

**Surprise:** `FakeGenerationStorage.update()` originally stored the same live `Generation` object reference on every call; since `GenerateDocument.execute()` mutates one `Generation` instance in place across two `update()` calls (`mark_in_progress()` then `complete()`/`fail()`), both recorded entries showed the final status — the intermediate `in_progress` snapshot was unobservable.
**Why:** Python objects are passed by reference; appending the same mutable object twice to a list doesn't create two independent snapshots.
**Impact:** Fixed by `copy.deepcopy(generation)` at record time in the fake. Any future fake that records objects mutated in place by the usecase under test needs the same snapshot discipline, or its call-history assertions silently collapse to the final state.
