# AI chat editing — Infrastructure Tests

This story adds a worker process, a queue broker and long-lived HTTP responses. Each is a
new way for the deployment to be wrong while the code is right.

---

## 1. Datastore availability

### 1.1 A datastore outage refuses edits cleanly instead of hanging
```gherkin
Given the datastore is unavailable
When a user submits an instruction
Then the request is refused with a server error within the configured timeout
And the response carries no internal detail
```

### 1.2 Edits work again after the datastore recovers, with no state left behind
```gherkin
Given the datastore was unavailable and has recovered
When a user submits an instruction
Then it is accepted and reaches a terminal state
And no edit left non-terminal by the outage remains non-terminal past its deadline
```

---

## 2. Queue broker availability

### 2.1 A broker outage does not accept edits that will never run
```gherkin
Given the queue broker is unavailable
When a user submits an instruction
Then either the request is refused
Or the edit is recorded and later executed once the broker recovers
And in neither case is the user shown a running edit that no worker will pick up
```

### 2.2 A worker started against a recovered broker drains the backlog without a stampede
```gherkin
Given a backlog of edits accumulated during a broker outage
When the worker resumes
Then the backlog is drained in bounded batches
And provider calls stay within the downstream rate limit
And the retries are not all attempted on the same tick
```

---

## 3. Configuration and proxy

### 3.1 Missing or invalid configuration fails at startup, in both processes
```gherkin
Given the configuration is missing or invalid for <setting>
When the web process starts
Then it fails to start with a message naming the setting
And the worker process fails the same way
```
Cover each setting separately, unset and blank: context-fit threshold, daily quota, edit
deadline, queue broker address, edit-provider selection, worker concurrency, downstream
provider rate limit, provider connect and read timeouts, client timeout, list page cap,
event retention bound, maximum document length, maximum instruction length, database pool
bound, canonical quota timezone. Every value the story's behaviour depends on fails the
boot; a value that silently falls back to a development default is the incident.

### 3.2 A non-development environment refuses to boot with the fake edit provider
```gherkin
Given the environment is not a development environment
And the edit provider is configured as the fake
When either process starts
Then it fails to start
```

### 3.3 The timer ordering invariant is validated at startup
```gherkin
Given a configuration where the provider timeout multiplied by its retry count is not
  less than the edit deadline
When either process starts
Then it fails to start naming the violated ordering
```
Also assert the deadline-versus-proxy-timeout and client-timeout-versus-deadline orderings,
each with the units stated in seconds.

### 3.4 The proxy streams the first chunk before the response completes
```gherkin
Given the deployed proxy configuration from the repository
When a client reads an edit's event stream through the proxy
Then the first chunk is observed before the response has completed
And the connection is not closed before the edit deadline
```
This asserts response buffering is disabled and the read timeout exceeds the edit
deadline — declared in `infra/`, never hand-edited on a host.

---

## 4. Hazard Guards

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

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the datastore is unavailable` | Database container stopped or connections refused |
| `the queue broker` | Redis instance backing the edit queue |
| `the worker process` | The arq worker entry point |
| `the deployed proxy configuration` | nginx configuration under `infra/` |
| `the edit deadline` | Env-configured maximum lifetime of one edit |
