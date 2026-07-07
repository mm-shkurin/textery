# Auto-generate: доклад — UI Tests

> **Implementation Order**: Tests are numbered for sequential TDD implementation.
> Start with page display (no logic needed), then interaction, then submission, then
> validation feedback, then server-response display, then navigation.

No prerequisite blocker screens apply to this story — there is no parent resource
(board/column-style dependency) that must exist before the generation form can render.

---

## 1. Page Display

### 1.1 The generation form displays the document type selector and input fields

```gherkin
Given a visitor opens the generation page
Then the document type selector shows all four document types
And "доклад" is shown as selected and available
And the other document types are shown as not yet available
And the topic, volume, requirements, and extra wishes fields are visible
```

---

## 2. User Interaction

### 2.1 The submit button is disabled until required fields are filled

```gherkin
Given a visitor is on the generation form
And the topic field is empty
Then the submit button is disabled

Given the visitor fills in a topic and a volume within range
Then the submit button becomes enabled
```

---

## 3. Form Submission

### 3.1 Submitting the form shows a loading state and transitions to the pending view

```gherkin
Given a visitor has filled in a valid generation request
When the visitor submits the form
Then the submit button shows a loading state
And the page transitions to the pending/in-progress view
```

### 3.2 Activating submit twice before a response arrives only creates one generation

```gherkin
Given a visitor has filled in a valid generation request
When the visitor activates the submit button twice in quick succession, before any
  response has come back
Then only one generation is created
And the second activation has no additional effect
```

---

## 4. Validation Feedback

### 4.1 An empty topic shows an inline error before submission reaches the server

```gherkin
Given a visitor leaves the topic field empty and moves focus away
Then an inline error is shown next to the topic field
And the form is not submitted
```

### 4.2 An out-of-range volume shows an inline error

```gherkin
Given a visitor enters a volume outside the 1-10 range
Then an inline error is shown next to the volume field
And the form is not submitted
```

---

## 5. Server Response Display

### 5.1 A completed generation displays the document content

```gherkin
Given the visitor's generation has finished successfully
When the pending view refreshes its status
Then the page shows the "completed" status
And the generated document's content is displayed
```

### 5.2 A failed generation displays an error state

```gherkin
Given the visitor's generation has failed
When the pending view refreshes its status
Then the page shows the "failed" status
And a friendly error message is displayed
And no internal error detail is shown
```

---

## 6. Navigation

### 6.1 "Create a new report" navigates back to the generation form

```gherkin
Given the visitor is viewing a completed document
When the visitor clicks "create a new report"
Then the visitor is returned to the generation form
```

### 6.2 "Create a new request" from the failed state navigates back to the generation form

```gherkin
Given the visitor is viewing a failed generation
When the visitor clicks "create a new request"
Then the visitor is returned to the generation form
```

---

## 7. Unsaved Input Protection

### 7.1 Navigating away with unfilled-but-entered form data warns before discarding it

```gherkin
Given a visitor has entered a topic and some requirements text but has not submitted
When the visitor attempts to navigate away or refresh the page
Then the visitor is warned that unsaved input will be lost
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---|---|
| `the document type selector shows all four document types` | 4 type cards rendered: доклад/эссе/сочинение/реферат |
| `shown as not yet available` | reduced-opacity card + "скоро" badge, non-interactive |
| `the submit button is disabled` | `<button disabled>` until `topic` and `volume_pages` (1-10) are both valid |
| `loading state` | button shows spinner, `POST /api/v1/generations` in flight |
| `pending/in-progress view` | client navigates to the status-polling screen for the returned `generation_id` |
| `inline error` | field-level validation message rendered on blur, before any network call |
| `the pending view refreshes its status` | client polls `GET /api/v1/generations/{generation_id}` |
| `no internal error detail is shown` | UI renders only the generic failed-state copy, never a raw provider error |
| `create a new report` / `create a new request` | button linking back to the generation form route |
| `activates the submit button twice in quick succession` | second click fires while the same client-generated `Idempotency-Key` is still in flight from the first click; button is disabled/debounced after the first activation |
| `warned that unsaved input will be lost` | browser `beforeunload` confirm prompt (or an in-app confirm dialog for in-app navigation) fires only when the topic/requirements/extra_wishes fields are non-empty |
