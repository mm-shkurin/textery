# Manual input mode (non-AI document creation) — Infrastructure Tests

No external service dependency exists in this story (no LLM/generation provider call),
so only database failure/recovery scenarios apply.

---

## 1. Database Connection Failure Handling

### 1.1 Document creation fails cleanly when the database is unavailable

```gherkin
Given the database is unreachable
When a client submits a manual-document creation request
Then the request fails with a clear server error
And no partial document record is left behind
```

### 1.2 Document save fails cleanly when the database is unavailable

```gherkin
Given the database is unreachable
When a client submits a save request for an existing document
Then the request fails with a clear server error
And the document's previously persisted content is unchanged
```

### 1.3 A failed manual-document creation never leaves a stray Generation row behind

```gherkin
Given the database write for a manual-document creation fails partway through
When the failure is handled
Then no Document row exists for the failed attempt
And no Generation row exists referencing the attempted document either — this path
  never creates one, even on failure
```

---

## 2. Database Recovery After Failure

### 2.1 Document creation and save succeed again once the database recovers

```gherkin
Given the database was unreachable and has since recovered
When a client retries a manual-document creation and save
Then both requests succeed normally
```

### 2.2 Many concurrent clients retrying after a shared recovery do not re-trigger the outage

```gherkin
Given many clients were all blocked by the same database outage
And the database has since recovered
When all of those clients retry their creation/save requests at once
Then their retries succeed without being synchronized into a single overwhelming spike
And the database does not fall back into an unavailable state under the retry burst
```

---

## 3. Startup Configuration Validation

### 3.1 The application fails fast at boot when required database configuration is missing

```gherkin
Given the database connection configuration is missing or blank
When the application starts up
Then startup fails immediately with a clear configuration error
And the application does not begin serving requests in a partially-configured state
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---|---|
| `the database is unreachable` | Postgres connection refused/timeout injected at the adapter boundary |
| `no partial document record is left behind` | no committed row for the failed creation attempt |
| `the document's previously persisted content is unchanged` | prior `content`/`version` values unchanged after the failed save |
| `has since recovered` | DB connectivity restored after the injected failure |
| `the database write for a manual-document creation fails partway through` | fault injected during the single insert underlying `POST /api/v1/documents` |
| `no Generation row exists referencing the attempted document` | `Generation` table row count for that `document_id` is zero, checked even on the failure path |
| `many clients ... retry ... at once` | M concurrent clients re-issue their blocked `POST`/`PUT` requests immediately after recovery is signaled |
| `not synchronized into a single overwhelming spike` | retry timestamps/connection-acquisition attempts show jitter/spread, not all landing in the same instant |
| `the database connection configuration is missing or blank` | DB connection string/credentials env var unset/blank at process start |
| `startup fails immediately` | application process exits non-zero / refuses to bind before serving traffic |
