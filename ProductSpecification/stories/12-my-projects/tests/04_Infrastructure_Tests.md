# Мои проекты — Infrastructure Tests

The feed's correctness depends on two things the application does not own: the database's
collation support and the configured bounds. Both fail silently in a small development
database and loudly in production, which is what these tests exist to invert.

---

## 1. Database Availability

### 1.1 The feed reports a database outage instead of an empty feed
```gherkin
Given the database is unreachable
When the caller requests their projects
Then the request fails as a server error
And no empty feed is returned
```

### 1.2 The feed recovers once the database returns
```gherkin
Given the database has been unreachable and the feed has failed
When the database becomes reachable again
Then a new request for the projects feed succeeds
And no restart is required
```

---

## 2. Configuration and Collation

### 2.1 A missing configuration key stops startup and names itself
```gherkin
Given the search statement timeout is not configured
When the application starts
Then startup fails
And the failure names the missing key
```

### 2.2 A database without the pinned collation is rejected at startup
```gherkin
Given a database that does not provide the pinned sort collation
When the application starts
Then startup fails naming the collation
And no request is served with an unpinned ordering
```

### 2.3 The search timeout does not outlive its request
```gherkin
Given a connection that has just served a search request
When that connection is reused for a long-running write
Then the write is not cut short by the search timeout
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|--------------------------|
| `the database is unreachable` | Container stopped / connection refused at the socket |
| `the search statement timeout` | `projects_search_statement_timeout_ms` |
| `the pinned sort collation` | `projects_sort_collation` (`ru-RU-x-icu`) — requires an ICU-enabled Postgres image |
| `does not outlive its request` | Timeout applied per transaction (`SET LOCAL`), never per session |
| `startup fails` | Non-zero exit with the key named in the message; no partially started app |
