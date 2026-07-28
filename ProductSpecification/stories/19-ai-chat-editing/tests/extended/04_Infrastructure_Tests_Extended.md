> These are additional edge case tests. Implement after core tests pass.

# AI chat editing — Infrastructure Tests (Extended)

### 1.1 The event table's retention bound is enforced
```gherkin
Given event rows older than the retention bound
When the pruning job runs
Then those rows are removed
And no event belonging to a non-terminal edit is removed
```

### 1.2 Deleting a document leaves no orphaned rows
```gherkin
Given a document with edits, events, revisions and messages
When the document is deleted
Then no edit, event, revision or message for it remains
And the deletion policy declared in the schema and in the mapping agree
```

### 1.3 A rolling deploy keeps the previous document paths working
```gherkin
Given the new tables have been migrated
And an instance running the previous code
When documents are read and saved through that instance
Then both succeed
```

### 1.4 The worker and the web process read the same configuration
```gherkin
Given a configuration value that differs between the two processes
When they start
Then the mismatch is detected rather than silently tolerated
```
