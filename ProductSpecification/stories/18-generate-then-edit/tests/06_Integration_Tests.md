# Generate → edit — Integration Tests

End-to-end across the generation flow, the conversion, and the editor, using the
deterministic fake generation provider.

---

## 1. Generate → Convert → Edit

### 1.1 A generated document flows from type selection to a saved edit
```gherkin
Given the fake provider is configured
When a user picks a type, the generation completes, it is converted, and the user saves an edit
Then a single document exists with the edited content
And the source generation is retained unchanged
```

---

## 2. Content Conversion Fidelity

### 2.1 Markdown output converts to the expected sanitized HTML
```gherkin
Given a completed generation whose content is markdown with headings, lists, and emphasis
When it is converted
Then the stored content is the corresponding sanitized HTML structure
And the markdown path emits no plain-text degrade signal
```

### 2.2 Plain-text output degrades safely
```gherkin
Given a completed generation whose content is plain text with no markdown
When it is converted
Then valid sanitized content is produced without error
And the degrade path emits a distinguishable operational signal
```

### 2.3 Empty output converts without crashing
```gherkin
Given a completed generation whose content is empty
When it is converted
Then a valid document is produced
```

---

## 3. Operability

### 3.1 A conversion failure after completion is observable
```gherkin
Given a generation that has completed
When its conversion fails
Then an error signal keyed by the generation is emitted
And the successful conversion path emits no such signal
```
