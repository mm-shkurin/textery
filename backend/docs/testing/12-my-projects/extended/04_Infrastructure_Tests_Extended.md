<!-- COPIED FILE. Source of truth: ProductSpecification/stories/12-my-projects/tests/extended/04_Infrastructure_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Мои проекты — Infrastructure Tests (Extended)

---

## 1. Migration

### 1.1 The migration is re-runnable after an interrupted concurrent index build
```gherkin
Given a concurrent index build that was interrupted and left an invalid index
When the migration is run again
Then it completes and leaves exactly one valid unique index
```

### 1.2 The migration aborts rather than blocking when it cannot take its lock
```gherkin
Given a long-running transaction holding a conflicting lock on generations
When the migration runs
Then it fails on its lock timeout
And the running sweep is not blocked behind it
```

### 1.3 The application starts against a database that has not yet been migrated
```gherkin
Given a deployment whose database is one migration behind
When the application starts
Then the mismatch is reported at startup rather than surfacing as a query error
```

---

## 2. Degraded Database

### 2.1 The statement deadline is applied per request, not per connection
```gherkin
Given a request that sets the statement deadline
When the connection is returned to the pool and reused
Then the next request on that connection runs without the inherited deadline
```

### 2.2 A database that answers slowly is bounded, not waited on
```gherkin
Given the database answers more slowly than the statement deadline allows
When the caller searches
Then the request is refused within the deadline
And the connection is returned to the pool
```

### 2.3 The feed survives a connection dropped mid-request
```gherkin
Given the database drops the connection while the feed is being read
When the caller requests their projects
Then the request fails cleanly
And a following request succeeds
```

---

## 3. Configuration Drift

### 3.1 Every configured bound is reported at startup
```gherkin
Given the application starts with its configuration complete
When it reports its readiness
Then each of the story's bounds is visible with the value in force
```

### 3.2 A deadline configured above the gateway's is rejected
```gherkin
Given a search statement deadline larger than the gateway's read timeout
When the application starts
Then startup fails naming both values
```

---

## 4. Search Slots

### 4.1 Search slots are released when the holding instance disappears
```gherkin
Given an instance holding a search slot is terminated mid-scan
When the slot's lifetime elapses
Then the account can search again
```

---

## DSL Technical Reference

Inherits `04_Infrastructure_Tests.md`.
