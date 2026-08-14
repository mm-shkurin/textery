<!-- COPIED FILE. Source of truth: ProductSpecification/stories/04-auto-generate-referat/tests/extended/02_UI_Tests_Extended.md
     Regenerate with `node scripts/sync-test-cases.mjs` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Auto-generate: реферат — UI Tests (Extended)

> These are additional edge case tests. Implement after core tests pass.

---

## 1. Copy Consistency Within a Run

### 1.1 One run names one type throughout

```gherkin
Given the user picked реферат
When the generation moves from pending to completed
Then every phrase on screen names the реферат
```

The chat panel keeps the whole progress transcript on screen across the state change, so
a phrase left hardcoded shows one type while its neighbour shows another — the same
document named two ways to the same user.

---

## 2. Switching Type

### 2.1 Choosing a different type re-labels the composer

```gherkin
Given the user picked реферат and returned to the type modal
When the user picks доклад instead
Then the composer names the доклад
```

Guards a stale type held in the flow state after a change of mind.

---

## 3. History

### 3.1 A generated реферат is listed as Реферат

```gherkin
Given the user generated a реферат
When the user opens their documents list
Then the row is labelled "Реферат"
And opening it restores the реферат type
```

The list receives the wire value and needs the display label; this product has already
shipped a bug where rows rendered the raw wire string.

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `every phrase on screen` | `generatingTitle`, `writingProgressMessage`, `writtenProgressMessage`, breadcrumb, topic heading |
| `the row is labelled` | `documentTypeLabelFromWire(wire)` |
| `restores the реферат type` | `documentTypeFromWire(wire)` returns `referat` |
