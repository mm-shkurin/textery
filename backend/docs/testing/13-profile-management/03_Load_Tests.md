<!-- COPIED FILE. Source of truth: ProductSpecification/stories/13-profile-management/tests/03_Load_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Profile management — Load Tests

The project's declared profile is **Throughput** (`ProductSpecification/ExpectedLoad.md`):
the binding constraint is request *rate*, not per-user data volume. This story converts a
zero-cost local token decode into a network call on effectively every authenticated page
view, which makes `GET /api/v1/auth/me` the highest-rate endpoint in the product — so the
story carries load scenarios even though it adds no queue, no external call and no scan.
That revises the interview's Performance paragraph; the reasoning is in
`13_ProfileManagement_Notes.md` § Load Considerations.

---

## 1. Profile Read at Page-View Rate

### 1.1 The profile read sustains the product's page-view rate without exhausting the pool
```gherkin
Given the configured throughput baseline
And accounts signed in at the product's concurrency target
When they read their profiles at the sustained page-view rate over the measurement window
Then every response reports the correct account's own profile
And the error rate stays under the ceiling
And no request fails waiting for a database connection
And checked-out connections return to their idle baseline once the window closes
```

*Threshold: the page-view rate implied by hundreds of concurrent users, sustained over the
window, error rate ≤ the project ceiling. Catches pool exhaustion and connection leaks on
the endpoint every authenticated page now depends on — a leak here degrades documents and
generations too, because they share the pool.*

### 1.2 The per-request database cost this scenario is sized against cannot drift silently
```gherkin
Given an authenticated account
When it reads its profile once
Then the number of account selects issued for that request is exactly the pinned count
```

*Pinned at **two**, not one (`endpoints.md` § Not decided here): the container opens one
session per dependency and the account-existence check is itself a dependency, so the
existence check and the profile read run on separate sessions — two selects, two
simultaneous checkouts, two liveness round-trips per request. Collapsing them to one is an
open ADR due before the backend scenarios; until it lands, this scenario is what stops 1.1's
sizing premise from silently becoming false in either direction.*

---

## 2. Rename Under Read Load

### 2.1 Renames do not stall the read path
```gherkin
Given the configured throughput baseline
And accounts reading their profiles at the sustained page-view rate
When a share of them rename themselves during the window
Then the read path holds its sustained rate
And the error rate stays under the ceiling
```

*Threshold: same sustained rate and error ceiling as 1.1, with the write share applied.
Catches a rename that takes a lock or holds a connection long enough to eat the read path's
headroom — the write is rare, the read is on every page, and they share one pool.*

---

### 2.2 The refusal paths return their connections too
```gherkin
Given the configured throughput baseline
When callers drive the refusal paths over the measurement window — unauthorized tokens,
  raw-cap refusals, name-bound refusals and oversized bodies
Then checked-out connections return to their idle baseline once the window closes
And no later request fails waiting for a database connection
```

*Threshold: same idle baseline as 1.1, measured after a window of refusals rather than
successes. Every other checkout assertion in this spec sits behind a successful driver or a
database that is down. A refusal aborts the request **after** the account-existence
dependency has already checked out its session — at two checkouts per request against a pool
of five plus ten overflow, a leak on that branch exhausts within a burst and takes documents
and generations down with it.*

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the configured throughput baseline` | The project's load-test baseline setup per `ProductSpecification/ExpectedLoad.md` |
| `the product's concurrency target` | Hundreds of concurrent users (`ExpectedLoad.md`) |
| `the sustained page-view rate` | Request rate over the measurement window, driven at the load runner |
| `reads their profiles` | `GET /api/v1/auth/me` with a valid access token |
| `no request fails waiting for a database connection` | No pool checkout timeout; SQLAlchemy default 5 + 10 overflow per process |
| `checked-out connections return to their idle baseline` | Pool checkout gauge sampled after the window |
| `the number of account selects issued` | `before_cursor_execute` capture, idiom of `test_generation_storage_cas_shape.py` |
| `the error rate ceiling` | The project's configured load error-rate ceiling |
