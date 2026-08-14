<!-- COPIED FILE. Source of truth: ProductSpecification/stories/04-auto-generate-referat/tests/02_UI_Tests.md
     Regenerate with `node scripts/sync-test-cases.mjs` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Auto-generate: реферат — UI Tests

> **Implementation Order**: Tests are numbered for sequential TDD implementation.
> Start with the type modal rendering the card as enabled (1.x), then selecting it and
> the copy that follows from the choice (2.x-3.x), then the wire (4.x).

---

## 1. Type Modal

### 1.1 The реферат card is offered

```gherkin
Given the user opens the document type modal
Then the реферат card is enabled
And it carries no "скоро" badge
```

### 1.2 The types without a story remain unavailable

```gherkin
Given the user opens the document type modal
Then the эссе and сочинение cards are still disabled
And each carries a "скоро" badge
```

Reads as a formality; it is the guard that the availability change was made per type and
not by removing the disabled treatment for everyone.

---

## 2. Composer Copy

### 2.1 The composer names the реферат

```gherkin
Given the user picked реферат
Then the topic field is headed "Тема реферата"
And the type is shown as реферат in the breadcrumb
```

Every declension for реферат already exists in the shared table but has never rendered,
because the card was disabled. A wrong form surfaces here for the first time.

---

## 3. Generating and Result

### 3.1 The generating screen names the реферат

```gherkin
Given the user picked реферат
When the user submits a topic
Then the generating screen reads "Готовим ваш реферат"
And the progress line reads "ИИ пишет реферат"
```

### 3.2 A failed реферат generation names the реферат

```gherkin
Given the user picked реферат
When the generation fails
Then the failure message names the реферат
And a retry is offered
```

---

## 4. Wire

### 4.1 Picking реферат generates a реферат

```gherkin
Given the user picked реферат
When the user submits a topic
Then the submitted request carries the реферат type
```

The defect this prevents has already happened once in this product: every card generated
a доклад because the picked type never reached the request. The card being newly enabled
is exactly when it could happen again.

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the document type modal` | Type-select modal over the landing |
| `the реферат card is enabled` | `DOCUMENT_TYPES` entry `referat` has `available: true`; card is clickable |
| `"скоро" badge` | Disabled-card treatment added by story 1 (not in the Figma export) |
| `the topic field is headed` | `topicFieldLabel(documentType)` from `shared/documentTypes.ts` |
| `the generating screen reads` | `generatingTitle(documentType)` |
| `the progress line reads` | `writingProgressMessage(documentType)` |
| `the failure message` | `generationFailedTitle(documentType)` |
| `carries the реферат type` | Request body `document_type: "реферат"` via `WIRE_DOCUMENT_TYPE` |
