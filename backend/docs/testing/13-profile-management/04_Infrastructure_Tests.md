<!-- COPIED FILE. Source of truth: ProductSpecification/stories/13-profile-management/tests/04_Infrastructure_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Profile management — Infrastructure Tests

Two concerns: the database being unavailable under an endpoint that every authenticated page
now depends on, and a migration landing on a populated `accounts` table across a fleet that
rolls one instance at a time.

---

## 1. Database Availability

### 1.1 A profile read with the database down fails cleanly
```gherkin
Given the database is unavailable
When an authenticated account reads its profile
Then the request fails as a server fault in this product's canonical failure form
And the response carries no database error text, no connection string and no stack trace
And the process stays up
```

### 1.2 A rename with the database down persists nothing and reports the fault
```gherkin
Given the database is unavailable
When an authenticated account renames itself
Then the request fails as a server fault
And once the database returns, a fresh read of the stored profile shows the name unchanged
```

### 1.2a A database that accepts the connection and never answers is abandoned
```gherkin
Given a database that accepts connections and never returns from the account select
When an authenticated account reads its profile
Then the request fails within a bounded statement wait
And it fails in this product's canonical failure form
And the connection is returned to the pool
```

*1.1 covers the database being **down** and the extended file covers the pool being
**exhausted**; neither covers it being **slow**. The pool's checkout timeout does not bound a
statement already running on a checked-out connection, so without a statement or socket
deadline a slow database converts into fleet-wide worker exhaustion on the product's
highest-rate endpoint.*

### 1.3 The profile read recovers once the database returns
```gherkin
Given the database was unavailable and a profile read failed
When the database becomes available again
Then the next profile read succeeds without restarting the application
```

---

## 2. Migration on a Live Fleet

### 2.1 Pre-story code keeps working against the new schema
```gherkin
Given a populated accounts table migrated to carry the name column
When registration, verification, sign-in and code resend run against it with the pre-story code path
Then each succeeds
And no pre-existing account row is altered
```

*N-1 code against N schema is live, not theoretical: instances roll one at a time, so the old
image serves traffic against the migrated table during the overlap.*

### 2.2 The migration adds the column without touching existing rows
```gherkin
Given a populated accounts table with accounts in several states
When the migration is applied
Then every pre-existing row keeps its email, verification status, registration date and failed-attempt count
And every pre-existing row reports no name
And the row count is unchanged
```

### 2.2a A row written by the pre-story image during the overlap reads back fine
```gherkin
Given the migration applied and an instance still running the pre-story image
When an account is registered through that old image
Then the insert succeeds
And a fresh read of that row through the new code returns a valid profile reporting no name
```

*2.1 asserts the old paths succeed and 2.2 asserts pre-existing rows survive; the case in
between — a row **created** during the overlap and read by the new code — is what a column
authored not-nullable, or a reader assuming non-null, breaks while both stay green.*

### 2.3 A rollback and re-apply leaves pre-existing data intact
```gherkin
Given a populated accounts table
When the migration is applied, rolled back, and applied again
Then every pre-existing row keeps its email, verification status, registration date and failed-attempt count
And the row count is unchanged
```

*The rollback drops the column, and with it every name entered since the deploy — accepted
and stated (`13_ProfileManagement_Notes.md` § Infrastructure Notes), not discovered later.
The sibling migration for the failed-attempt count really does drop its column on downgrade,
so this is the established behaviour, not a hypothetical.*

---

## 3. Configuration

### 3.0 The application refuses to start with a profile-path setting missing
```gherkin
Given the application configured with the request body cap unset
And configured with the connection pool size unset
And configured with the access-token lifetime unset
When it starts with each in turn
Then it fails to start immediately naming the missing setting
And it does not fall back to a framework or development default
```

*Each of these degrades lazily at first use today. On the endpoint every authenticated page
depends on, a silent fallback is discovered as a production symptom rather than a failed
deploy.*

### 3.0a The timeout budget nests in the required order
```gherkin
Given the client's bounded wait, the proxy's read timeout, and the backend's
  checkout and statement budgets multiplied by its retry count
Then the innermost worst-case total is strictly less than each enclosing deadline
And a change to any of them that inverts the order fails the check
```

*The same shape 3.1 gives the body caps, applied to time — otherwise the client gives up
first and leaves inner work in flight, or the proxy cuts a response mid-commit, and either
drifts silently the next time someone tunes one number.*

### 3.1 The proxy's body cap sits above the application's
```gherkin
Given the frontend proxy configuration that fronts the API
Then it declares a request body cap
And that cap is greater than the application's own body cap
```

*Unset today, so the proxy's 1 MiB default is the real ceiling and it answers with an HTML
error page rather than this product's failure form — which would make the canonical
size refusal unreachable for every browser while a backend-port test went green
(`endpoints.md` § Corrected after the review passes). The existing configuration-reading
check under `frontend/scripts/` is the place this assertion belongs.*

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the database is unavailable` | Postgres container stopped / connections refused for the duration |
| `this product's canonical failure form` | `{"error_code": …, "message": …}` via `exception_handlers.py` |
| `a fresh read of the stored profile` | Re-read through a new session against real Postgres |
| `the pre-story code path` | The application image built from the commit before this story's migration |
| `the migration` | The Alembic revision adding the nullable `name` column to `accounts` |
| `the frontend proxy configuration` | `infra/docker/nginx/frontend.conf`, which proxies `/api/` |
| `the application's own body cap` | 2 MiB (`api-specs/README.md` § Request Body Cap) |
