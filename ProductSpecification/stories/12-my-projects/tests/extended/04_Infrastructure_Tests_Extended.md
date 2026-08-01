> These are additional edge case tests. Implement after core tests pass.

# Мои проекты — Infrastructure Tests (Extended)

## 1. The migration is re-runnable after an interrupted concurrent index build

```gherkin
Given a concurrent index build that was interrupted and left an invalid index
When the migration is run again
Then it completes and leaves exactly one valid unique index
```

## 2. The migration aborts rather than blocking when it cannot take its lock

```gherkin
Given a long-running transaction holding a conflicting lock on generations
When the migration runs
Then it fails on its lock timeout
And the running sweep is not blocked behind it
```

## 3. The application starts against a database that has not yet been migrated

```gherkin
Given a deployment whose database is one migration behind
When the application starts
Then the mismatch is reported at startup rather than surfacing as a query error
```

## 4. The statement timeout is applied per request, not per connection

```gherkin
Given a request that sets the statement deadline
When the connection is returned to the pool and reused
Then the next request on that connection runs without the inherited deadline
```

## 5. Search slots are released when the holding instance disappears

```gherkin
Given an instance holding a search slot is terminated mid-scan
When the slot's lifetime elapses
Then the account can search again
```
