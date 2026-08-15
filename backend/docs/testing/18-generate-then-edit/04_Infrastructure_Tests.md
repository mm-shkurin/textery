<!-- COPIED FILE. Source of truth: ProductSpecification/stories/18-generate-then-edit/tests/04_Infrastructure_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Generate → edit — Infrastructure Tests

Covers the schema evolution, the concurrency-closing constraint, and config drift for the
new conversion path.

---

## 1. Schema Migration

### 1.1 The generation_id column is additive and nullable
```gherkin
Given the documents table before the migration
When the migration adds the generation_id column
Then existing document rows are valid with a null generation_id
And no existing column is renamed or dropped
```

### 1.2 Old code survives the new column during a rolling deploy
```gherkin
Given the pre-migration application code
When it inserts and reads documents against the migrated schema
Then both operations succeed without error
```

---

## 2. Concurrency Constraint

### 2.1 A unique constraint on generation_id rejects a second document
```gherkin
Given a document already linked to a generation
When a second insert for the same generation is attempted at the storage level
Then the storage rejects it
```

---

## 3. Referential Integrity

### 3.1 The generation link has a defined on-delete policy
```gherkin
Given a document linked to a generation
When that generation is deleted
Then the defined on-delete policy applies
And no document is left with a dangling generation reference
```

---

## 4. Config & Dependency

### 4.1 The conversion path is pinned against the production provider output shape
```gherkin
Given the generation output shape the production provider actually returns
When conversion runs against that shape
Then it produces valid sanitized content
And the test fails if only the fake provider's format is handled
```

### 4.2 The markdown dependency passes the vulnerability audit
```gherkin
Given the new markdown-parser dependency in the lockfile
When the dependency audit runs
Then it reports no known vulnerability
```
