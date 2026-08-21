> These are additional edge case tests. Implement after core tests pass.

# Analytics Event Tracking — Infrastructure Tests (Extended)

---

## 1. Migration Against a Populated Database

### 1.1 The new columns land on a table that already holds accounts
```gherkin
Given a database holding accounts created before this feature
When the migration runs
Then it completes
And every existing account still reads
And every new value on those accounts reads as unset
```

### 1.2 The migration is reversible in the same sense as its predecessors
```gherkin
Given the migration has been applied
When it is reversed
Then the schema returns to its previous shape
And the reversal is only ever reached by an explicit operator command
```

---

## 2. Rolling Deployment

### 2.1 An older instance can still delete an account after the schema has moved
```gherkin
Given the new schema is live
And an instance running the previous release
When an account holding recorded events deletes itself through that instance
Then the deletion succeeds
And its events remain, attached to no account
```

This is the window a rolling deployment actually opens: the migration runs before the new
code is everywhere, so for a few minutes the deletion path in service is one that knows
nothing about the events table.

### 2.2 An older instance can still register an account
```gherkin
Given the new schema is live
And an instance running the previous release
When a visitor registers through that instance
Then the registration succeeds
And the account's new values read as unset
```

---

## 3. Pool Behaviour

### 3.1 A saturated connection pool recovers once load subsides
```gherkin
Given sustained load that drives the connection pool to its ceiling
When the load stops
Then connections in use return to their resting level
And subsequent operations succeed without waiting on the pool
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `accounts created before this feature` | Rows inserted with the pre-migration column set |
| `an instance running the previous release` | The application booted from the commit before this story |
| `connections in use` | SQLAlchemy pool `checkedout()` |
