> These are additional edge case tests. Implement after core tests pass.

# AI chat editing — Security Tests (Extended)

### 1.1 An idempotency key from another account cannot reach that account's edit
```gherkin
Given an edit created by another account with a known idempotency key
When the caller submits an instruction reusing that key
Then a new edit is created for the caller
And the other account's edit is not returned and not altered
```

### 1.2 A cancelled edit cannot be revived
```gherkin
Given a cancelled edit
When the caller submits its identifier to every endpoint that accepts one
Then no endpoint returns it to a running state
```

### 1.3 Instruction text is never interpreted as markup anywhere it is displayed
```gherkin
Given an instruction containing markup
When it is shown in the chat history
Then it is displayed literally
```

### 1.4 Paging parameters cannot be used to enumerate other documents
```gherkin
Given an authenticated user
When they craft a cursor referring to another account's document
Then the request is refused
And no entry from that document is returned
```

### 1.5 A quota refund cannot be triggered repeatedly
```gherkin
Given an edit that has already been refunded
When a refund is triggered again for the same edit
Then the counter is unchanged
```
