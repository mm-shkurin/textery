> These are additional edge case tests. Implement after core tests pass.

# Generate → edit — Infrastructure Tests (Extended)

## 1. Response Compatibility

### 1.1 An existing consumer tolerates the new response fields
```gherkin
Given a consumer built before generation_id and title existed
When it reads a document response carrying those fields
Then it does not reject the payload
```

## 2. Migration Reversibility

### 2.1 The migration is reversible without data loss on manual documents
```gherkin
Given documents created before and after the migration
When the migration is rolled back
Then manual documents remain intact
```
