> **Implementation Order**: hazard-scan guards, continuing `04_Infrastructure_Tests.md`.

# AI chat editing — Infrastructure Tests (hazard guards)

DSL reference: see the table at the end of `04_Infrastructure_Tests.md`.


Folded in from the hazard-catalogue scan.

### 4.1 A missing threshold or quota setting fails closed, never open
```gherkin
Given the context-fit threshold or the daily quota is absent or unparseable
When a whole-document instruction is submitted
Then it is refused
And no unbounded content is sent to the provider
```
The permissive fall-through here spends money against a paid model.

### 4.2 A batch that fails on one item still processes the rest and names the failure
```gherkin
Given a batch of items for <job>
When one item fails mid-batch
Then the items completed before it stay completed
And the items after it are still attempted
And the outcome names the failed item, not only a count
And a re-run retries only the failed item
```
Cover each separately: <job> ∈ {stale-edit reclaim, broker-recovery drain, event pruning}.

### 4.3 Every degraded path emits an attributable signal and the healthy path emits none
```gherkin
Given <degraded path>
When it is exercised
Then a signal carrying the edit identifier and the document or account identifier is
  emitted
And exercising the healthy path emits no such signal
```
Cover each separately: <degraded path> ∈ {stale-edit reclaim, quota refund, cancellation,
client-timeout terminalisation, retry give-up after the attempt cap, replay from the start
after an unusable last-event value, broker-outage degraded submission}.

### 4.4 A reaper that stops running is detectable
```gherkin
Given the stale-edit reaper
When it completes an activation
Then its last-run time and its reclaim count are observable
And an activation that has not run within its interval is distinguishable from one that
  ran and reclaimed nothing
```
The reaper is the only safety net for dropped and abandoned edits; silent death of the
scheduler is otherwise visible only as user complaints.

### 4.5 Pruning with an absent or zero retention bound affects no rows
```gherkin
Given the event retention bound is absent, empty or zero
When the pruning job runs
Then no rows are removed
```
Assert the boundary too: a row exactly at the bound and a row one tick inside it.

### 4.6 Deleting an edit leaves no orphaned events
```gherkin
Given an edit with recorded events
When the edit row is removed
Then no event row for it remains
And the schema's delete policy and the mapping's cascade agree for that relationship
```

### 4.7 A record written before this feature reads back with defined defaults
```gherkin
Given a document row created before this story's migration
When it is read by the new code
Then it is returned with a defined default for every field the migration added
And no read fails on a missing value
```

### 4.8 Revision history has a stated growth bound
```gherkin
Given a document with more revisions than the retention policy allows
When the retention policy is applied
Then revisions beyond the bound are removed
And every revision the policy declares restorable remains restorable
```
If the project decides revisions are unbounded by design, this scenario is replaced by an
explicit statement of that decision — the one outcome not allowed is leaving it unsaid,
since each revision holds up to a full document.

### 4.9 A request for a new path landing on an old instance degrades, never errors
```gherkin
Given a rolling deploy with instances on both code versions
When a request for one of this story's endpoints lands on an instance running the
  previous version
Then it is refused with a defined response
And no stale content is written over a newer version
```

---
