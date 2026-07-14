> These are additional edge case tests. Implement after core tests pass.

# Manual input mode (non-AI document creation) — UI Tests (Extended)

## 1. Formatting Edge Cases

### 1.1 Toggling a numbered list off returns to plain paragraphs

```gherkin
Given the editor content is a numbered list
When the visitor toggles the numbered-list button off with the list selected
Then the content reverts to plain paragraphs, not an empty list wrapper
```

## 2. Unsaved State

No test-spec scenario asserts a navigate-away/refresh confirm-guard for unsaved editor
content. This is deliberate, not an oversight: the story spec (`05_ManualMode.md`, Core
Requirements) explicitly names unsaved-edit loss on navigation as an **accepted,
temporary posture** in this story — no autosave, no confirm-guard — with that
protection owned by story #10. Adding a warn-before-discard test here would contradict
the spec's own stated scope; that guard belongs in story #10's test-spec once autosave
lands.

## 3. Reopen Edge Cases

### 3.1 Reopening a document that was never saved shows the empty editor, not an error

```gherkin
Given a manual document was created but no save has ever succeeded for it
When the visitor reopens that document
Then the editor shows an empty content area, not an error state
```
