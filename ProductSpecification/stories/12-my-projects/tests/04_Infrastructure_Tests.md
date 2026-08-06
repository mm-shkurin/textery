# Мои проекты — Infrastructure Tests

The feed is a pure read, so its infrastructure surface is the database connection, the one
migration this story ships, and the two things the application does not own: the database's
collation support and the configured bounds. The migration is the interesting part:
`generations` is a populated table written continuously by the stale sweep in every replica,
which the `documents` migration it mirrors was not. Collation and configuration fail silently
in a small development database and loudly in production, which is what these tests invert.

---

## 1. Database Availability

### 1.1 The feed fails cleanly when the database is unavailable
```gherkin
Given the database is unavailable
When a caller requests their projects
Then the request is refused with a generic error
And no empty feed is returned
And the response exposes no connection or query detail
```

### 1.2 The feed recovers once the database returns
```gherkin
Given the database was unavailable and a projects request failed
When the database becomes available again
And the caller requests their projects
Then the feed is returned
And no restart was required
```

---

## 2. Migration Against a Populated Table

### 2.1 The migration completes on a table that already has generations
```gherkin
Given a database holding generations for several accounts, none carrying an idempotency key
When the migration runs
Then it completes
And every pre-existing generation is still readable and listable
```

### 2.2 The new constraint holds for new rows without rejecting old ones
```gherkin
Given a database migrated from a populated generations table
When one account submits two generations with the same idempotency key
Then the second is answered with the first rather than stored twice
And the pre-existing keyless generations remain unaffected
```

### 2.3 The migration does not block the running sweep
```gherkin
Given a database holding generations and a stale sweep running against it
When the migration runs
Then the sweep continues to claim and requeue stale rows
And the migration does not wait indefinitely for a lock
```

### 2.4 The previous code version keeps writing against the migrated schema
```gherkin
Given a database migrated to head
When the previous application version creates two generations for one account
  without supplying an idempotency key
Then both are stored
And neither collides on the new unique index
And both are listed by the new feed
And the sweep's updates against those rows keep succeeding
```

---

## 3. Configuration and Collation

### 3.1 A required constant that is unset or unparsable stops startup
```gherkin
Given a required constant is unset, blank or non-numeric
When the application starts
Then startup fails naming that constant
And the failure does not surface later as an error on the first request
```

### 3.2 A documented default is in effect and observable when its variable is unset
```gherkin
Given a constant whose default is documented and whose variable is unset
When the application starts
Then the documented default is in effect
And it is observable in the behaviour it governs
```

### 3.3 A database without the pinned collation is rejected at startup
```gherkin
Given a database that does not provide the pinned sort collation
When the application starts
Then startup fails naming the collation
And no request is served with an unpinned ordering
```

### 3.4 The search deadline does not outlive its request
```gherkin
Given a connection that has just served a search request
When that connection is reused for a long-running write
Then the write is not cut short by the search deadline
```

---

## 4. Search Slot Lifecycle

### 4.1 Reclaiming an expired search slot leaves live slots intact
```gherkin
Given one account's search slot has expired
And two other accounts hold live slots
When reclamation runs
Then only the expired slot is removed
And both live accounts still shed a second concurrent search
And a reclamation run with nothing expired removes no rows
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the database is unavailable` | Compose-level stop of the database container (existing infra-test harness) |
| `the migration runs` | `alembic upgrade head` against the seeded database |
| `the stale sweep` | `RequeueStaleGenerations`, run from every replica's lifespan |
| `does not wait indefinitely for a lock` | `lock_timeout` set; unique index built `CONCURRENTLY` |
| `the pinned sort collation` | `ru-RU-x-icu` — requires an ICU-enabled Postgres image |
| `the search deadline` | 3 s, applied per transaction (`SET LOCAL`), never per session |
| `startup fails` | Non-zero exit with the key named in the message; no partially started app |
