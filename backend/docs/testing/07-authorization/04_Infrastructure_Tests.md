<!-- COPIED FILE. Source of truth: ProductSpecification/stories/07-authorization/tests/04_Infrastructure_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Authorization — Infrastructure Tests

## 1. Database connection failure during auth request

```gherkin
Given the database is unreachable
When a client submits any auth request (register, verify, resend, login, refresh)
Then the response is a generic 500 error, no internal detail leaked
And the request is not left partially applied
```

## 2. Database recovery after failure

```gherkin
Given the database was unreachable and has now recovered
When a client submits an auth request
Then the request succeeds normally, no lingering degraded state
```

## 3. JWT signing secret misconfiguration at startup

```gherkin
Given the JWT signing secret is missing or malformed in configuration
When the application starts
Then startup fails fast with a clear configuration error
And the service does not start in a state that would silently issue unsigned or
    unverifiable tokens
```
