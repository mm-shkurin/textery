> **Implementation Order**: hazard guards for the editor extension — fold into the same
> TDD cycles as 07. Autosave/title safety, then migration & dirty-state.

# Story 5 — Editor Extension Hazard Tests

Companion to 07. Forced guards from the hazard scan of the editor extension.

## 9. Autosave & Title Hazards

### 9.1 A content-only autosave does not wipe the title
```gherkin
Given a document with a title, open in the editor
When a content-only autosave that omits the title is sent
Then the stored title is unchanged
```
Cover the trio: title omitted → unchanged; null → cleared; value → set.

### 9.2 Out-of-order autosaves preserve the newest content
```gherkin
Given content A then content B autosaved with A's response arriving last
When the responses resolve
Then the persisted and shown content is B, and B is not lost
```

### 9.3 Autosave failures are handled per kind
```gherkin
Given an autosave that fails
When the failure is a transient timeout or 5xx
Then it retries with backoff and a capped attempt count
When the failure is an expired session
Then the user is prompted to re-authenticate, not left in a silent failed state
```

### 9.4 Rapid typing coalesces to a bounded save rate
```gherkin
Given the user types continuously
When autosave runs
Then many edits collapse into few requests, not one per keystroke
```

### 9.5 An autosave with an absent or unparseable version fails closed
```gherkin
Given an autosave whose version is missing or unparseable
When it is processed
Then it is rejected, never a silent overwrite
```

### 9.6 Server-owned fields on save are ignored (title added)
```gherkin
Given a save body carrying title plus id, version, status, owner, and created-at
When it is processed
Then only content and title are written; the rest keep their server values
```

### 9.7 The title length limit is measured in the pinned unit
```gherkin
Given a multibyte title straddling the length boundary
When it is saved
Then it is accepted or rejected against the pinned counting unit
```

## 10. Migration & Dirty State

### 10.1 A legacy document survives load-edit-save without content loss
```gherkin
Given a document saved under the old inline-only schema
When it is opened, edited, saved, and reloaded
Then the previously-stored content is preserved, or the lossy transform is explicitly defined and asserted
```

### 10.2 Multibyte content round-trips byte-exact after normalization
```gherkin
Given content with a combining accent, an emoji, and CJK
When it is saved and reloaded
Then it equals the source byte-for-byte after NFC normalization
```

### 10.3 Leaving with unsaved or failed-autosave edits is guarded
```gherkin
Given the editor holds edits not yet persisted, or a failed autosave
When the user navigates away, refreshes, or the session expires mid-save
Then they are warned or the draft is restored, not silently lost
```

### 10.4 The title column tolerates rolling deploy
```gherkin
Given the additive nullable title column
When pre-migration code reads and serves documents, and an existing row has no title
Then both succeed, and the migration is safe if applied by more than one session
```
