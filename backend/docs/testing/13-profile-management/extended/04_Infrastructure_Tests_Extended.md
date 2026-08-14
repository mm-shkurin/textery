<!-- COPIED FILE. Source of truth: ProductSpecification/stories/13-profile-management/tests/extended/04_Infrastructure_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Profile management — Infrastructure Tests (Extended)

---

## 1. Partial Availability

### 1.1 A saturated connection pool refuses cleanly rather than hanging
```gherkin
Given every database connection is checked out
When an authenticated account reads its profile
Then the request fails within its bounded wait
And it fails in this product's canonical failure form
And the process stays up
```

### 1.2 An application restart mid-request loses nothing already committed
```gherkin
Given an authenticated account that renamed itself successfully
When the application is restarted
Then a fresh read of the stored profile still reports the new name
```

---

## 2. Migration Edges

### 2.1 The migration is safe to apply twice
```gherkin
Given a populated accounts table already carrying the name column
When the migration is applied again
Then it completes without altering any row
```

### 2.2 Names survive a rolling deploy in both directions
```gherkin
Given a populated accounts table migrated to carry the name column
And accounts that have set names
When one instance runs the pre-story image while another runs the new one
Then reads and sign-ins succeed against both
And no stored name is lost
```

---

## 3. Configuration Drift

### 3.1 The proxy body cap and the application body cap stay in their required order
```gherkin
Given the proxy configuration and the application's declared body cap
Then the proxy's cap is strictly greater than the application's
And a change to either that inverts the order fails the check
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `every database connection is checked out` | Pool exhausted by held sessions for the duration |
| `its bounded wait` | SQLAlchemy pool checkout timeout |
| `this product's canonical failure form` | `{"error_code": …, "message": …}` |
| `the pre-story image` | Application built from the commit before this story's migration |
| `the proxy configuration` | `infra/docker/nginx/frontend.conf` |
| `the application's declared body cap` | 2 MiB (`api-specs/README.md`) |
