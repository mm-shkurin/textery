> These are additional edge case tests. Implement after core tests pass.

# Manual input mode (non-AI document creation) — API Tests (Extended)

## 1. Idempotency Edge Cases

### 1.1 Different idempotency keys for otherwise-identical create requests create separate documents

```gherkin
Given two identical manual-document creation requests submitted with different
  idempotency keys
When both are submitted
Then two separate documents are created
```

## 2. Save Edge Cases

### 2.1 Saving with an empty content string is accepted

```gherkin
Given a manual document exists
When the client saves with an empty content string and the current version
Then the request is accepted and the document's content becomes empty
```

### 2.2 A save request missing the version field is rejected

```gherkin
Given a manual document exists
When the client submits a save request without a version field
Then the response is a validation error
```

## 3. Nullable Link Compatibility

### 3.1 Existing story #1 document-reading paths tolerate a manual document's null generation link

```gherkin
Given a manual document exists with no linked generation
When it is read through an existing story #1 document-reading path
Then the read succeeds without error, treating the missing generation link as absent
```

### 3.2 Story #1's generation-completion path can never mutate a manual document's status

```gherkin
Given a manual document exists with status "draft" and no linked generation
When story #1's generation-completion/status-update path is invoked against that
  document's id (no matching Generation exists for it)
Then the operation is rejected or is a no-op
And the manual document's status remains "draft", never silently pushed to
  "completed" or "failed" by a code path that assumes every Document has a Generation
```

