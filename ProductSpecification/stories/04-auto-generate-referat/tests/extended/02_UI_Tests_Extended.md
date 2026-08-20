# Auto-generate: реферат — UI Tests (Extended)

> These are additional edge case tests. Implement after core tests pass.

Screens: the generation composer and its chat panel, the document-type modal, and the
documents list. Copy source: `frontend/src/shared/copy/documentTypeCopy.ts`.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.referat@textery.test` / `Qa!Referat2026` |
| Topic typed into the composer | `Влияние цифровизации на образование` |
| Реферат phrases | `Тема реферата`, `Готовим ваш реферат`, `ИИ пишет реферат`, `Пишу реферат`, breadcrumb `Реферат` |
| Доклад phrases | `Тема доклада`, `Готовим ваш доклад`, `ИИ пишет доклад`, breadcrumb `Доклад` |
| List label | `documentTypeLabelFromWire("реферат")` → `Реферат` |
| Wire value | `document_type: "реферат"` |

---

## 1. Copy Consistency Within a Run

### TC-04-UI-EXT-1.1 — One run names one type throughout

| Field | Value |
|---|---|
| Description | The chat panel keeps the whole progress transcript on screen across the state change, so a phrase left hardcoded shows one type while its neighbour shows another — the same document named two ways to the same user. |
| Preconditions | Account A signed in; реферат picked; the stub completes the generation after the pending screen has been read. |
| Test data | The five реферат phrases above; the generation moves `pending` → `completed` without a remount |
| Steps | 1. Pick `Реферат`, type the topic, submit.<br>2. While `pending`, read the composer heading, the breadcrumb, the generating title and the chat progress line.<br>3. Let the generation complete.<br>4. Re-read every phrase still on screen, including the earlier transcript lines. |
| Expected result | Before and after completion the screen reads `Тема реферата`, `Реферат`, `Готовим ваш реферат`, `ИИ пишет реферат` and `Пишу реферат`; the substring `доклад` appears nowhere on the page at either point. |
| Status | Not run |

---

## 2. Switching Type

### TC-04-UI-EXT-2.1 — Choosing a different type re-labels the composer

| Field | Value |
|---|---|
| Description | Guards a stale type held in the flow state after a change of mind — the composer would keep реферат copy while the request carried доклад, or the reverse. |
| Preconditions | Account A signed in; реферат already picked and the composer showing `Тема реферата`. |
| Test data | Second choice `Доклад`; expected wire value `доклад` |
| Steps | 1. Return to the document-type modal from the composer.<br>2. Pick `Доклад`.<br>3. Read the composer heading and the breadcrumb.<br>4. Submit the topic and inspect the captured request body. |
| Expected result | The heading reads `Тема доклада` and the breadcrumb `Доклад`; no реферат phrase remains on screen; the captured `POST /api/v1/generations` body carries `document_type: "доклад"`. |
| Status | Not run |

---

## 3. History

### TC-04-UI-EXT-3.1 — A generated реферат is listed as Реферат

| Field | Value |
|---|---|
| Description | The list receives the wire value and needs the display label; this product has already shipped a bug where rows rendered the raw wire string. |
| Preconditions | Account A signed in and has one completed реферат with topic `Влияние цифровизации на образование`. |
| Test data | Row wire value `реферат`; expected label `Реферат`; internal id after reopening `referat` |
| Steps | 1. Open the documents list.<br>2. Read the type label on the реферат row.<br>3. Click the row to open it.<br>4. Read the type shown on the opened document. |
| Expected result | The row is labelled exactly `Реферат` (capitalised display label, not the raw lowercase wire string `реферат`); opening it shows `Реферат` and the composer copy declines as реферат (`Тема реферата`), proving `documentTypeFromWire("реферат")` returned `referat`. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `every phrase on screen` | `generatingTitle`, `writingProgressMessage`, `writtenProgressMessage`, breadcrumb, topic heading |
| `the row is labelled` | `documentTypeLabelFromWire(wire)` |
| `restores the реферат type` | `documentTypeFromWire(wire)` returns `referat` |
