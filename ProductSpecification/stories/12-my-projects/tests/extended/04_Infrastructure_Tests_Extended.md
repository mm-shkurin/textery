> These are additional edge case tests. Implement after core tests pass.

# Мои проекты — Infrastructure Tests (Extended)

---

## 1. Degraded Database

### 1.1 A database that answers slowly is bounded, not waited on
```gherkin
Given the database answers more slowly than the search timeout allows
When the caller searches
Then the request is refused within the timeout
And the connection is returned to the pool
```

### 1.2 The feed survives a connection dropped mid-request
```gherkin
Given the database drops the connection while the feed is being read
When the caller requests their projects
Then the request fails cleanly
And a following request succeeds
```

---

## 2. Configuration Drift

### 2.1 Every configured bound is reported at startup
```gherkin
Given the application starts with its configuration complete
When it reports its readiness
Then each of the story's bounds is visible with the value in force
```

### 2.2 A timeout configured above the gateway's is rejected
```gherkin
Given a search statement timeout larger than the gateway's read timeout
When the application starts
Then startup fails naming both values
```

---

## DSL Technical Reference

Inherits `04_Infrastructure_Tests.md`.
