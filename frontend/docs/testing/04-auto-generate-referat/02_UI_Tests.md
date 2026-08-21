<!-- COPIED FILE. Source of truth: ProductSpecification/stories/04-auto-generate-referat/tests/02_UI_Tests.md
     Regenerate with `node scripts/sync-test-cases.mjs` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Auto-generate: реферат — UI Tests

> **Implementation Order**: Tests are numbered for sequential TDD implementation.
> Start with the type modal rendering the card as enabled (1.x), then selecting it and
> the copy that follows from the choice (2.x-3.x), then the wire (4.x).

Screens: the document-type modal over «Мои проекты», the generation composer, the
generating screen and its chat panel. Copy source: `frontend/src/shared/documentTypes.ts`
and `frontend/src/shared/copy/documentTypeCopy.ts`.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.referat@textery.test` / `Qa!Referat2026` |
| Topic typed into the composer | `Влияние цифровизации на образование` |
| Volume | `5` страниц |
| Реферат card | label `Реферат`, description `Изложение темы с выводами`, internal id `referat` |
| «скоро» badge | `<span class="soon-pill">скоро</span>`, rendered only when `option.available` is false |
| Wire value for реферат | `document_type: "реферат"` (`WIRE_DOCUMENT_TYPE.referat`) |
| Create endpoint | `POST /api/v1/generations` |

---

## 1. Type Modal

### TC-04-UI-1.1 — The реферат card is offered

| Field | Value |
|---|---|
| Description | The story's user-visible change. If the card stays disabled, nothing else in this file is reachable. |
| Preconditions | Account A signed in and on «Мои проекты»; `DOCUMENT_TYPE_AVAILABLE.referat` is `true`. |
| Test data | Card `Реферат`, description `Изложение темы с выводами` |
| Steps | 1. Click «Создать проект» to open the document-type modal.<br>2. Locate the card headed `Реферат`.<br>3. Click it. |
| Expected result | The `Реферат` card is clickable — no `disabled` attribute, no disabled styling — and renders no `скоро` badge; clicking it selects реферат and advances to the composer. |
| Status | Not run |

### TC-04-UI-1.2 — The types without a story remain unavailable

| Field | Value |
|---|---|
| Description | Reads as a formality; it is the guard that the availability change was made per type and not by removing the disabled treatment for everyone. |
| Preconditions | Account A signed in; the document-type modal open. |
| Test data | Cards `Эссе` and `Сочинение` |
| Steps | 1. Open the document-type modal.<br>2. Read the `Эссе` card's enabled state and badge.<br>3. Read the `Сочинение` card's enabled state and badge.<br>4. Click each and observe whether the composer opens. |
| Expected result | Both cards are non-interactive (`disabled`) and each renders the text `скоро` in its `soon-pill` badge; clicking neither opens the composer. Only `Реферат` and `Доклад` are selectable. |
| Status | Not run |
| Note | Stories #2 and #3 flip `DOCUMENT_TYPE_AVAILABLE.essay` / `.sochinenie` to `true`; from that point this case's expected result belongs to those stories, not to this one. |

---

## 2. Composer Copy

### TC-04-UI-2.1 — The composer names the реферат

| Field | Value |
|---|---|
| Description | Every declension for реферат already exists in the shared table but has never rendered, because the card was disabled. A wrong form surfaces here for the first time. |
| Preconditions | Account A signed in; реферат picked in the type modal. |
| Test data | `topicFieldLabel('referat')`, `DOCUMENT_TYPE_LABELS.referat` |
| Steps | 1. Pick `Реферат` in the modal.<br>2. Read the heading above the topic input.<br>3. Read the type shown in the breadcrumb. |
| Expected result | The topic field heading reads exactly `Тема реферата` (genitive, not `Тема Реферат`); the breadcrumb shows `Реферат`. Neither string contains `доклад` in any form. |
| Status | Not run |

---

## 3. Generating and Result

### TC-04-UI-3.1 — The generating screen names the реферат

| Field | Value |
|---|---|
| Description | The generating title and the chat progress line sat hardcoded as `доклад`; with the card enabled, a реферат run is the first time the mismatch is visible to a user. |
| Preconditions | Account A signed in; реферат picked; the backend/stub keeps the generation in `pending`/`in_progress` long enough to read the screen. |
| Test data | Topic `Влияние цифровизации на образование`; `generatingTitle('referat')`, `writingProgressMessage('referat')` |
| Steps | 1. Pick `Реферат`, type the topic, submit.<br>2. Read the generating screen's title.<br>3. Read the progress line in the chat panel. |
| Expected result | The title reads exactly `Готовим ваш реферат` (possessive `ваш`, not `ваше`) and the progress line reads exactly `ИИ пишет реферат`. |
| Status | Not run |

### TC-04-UI-3.2 — A failed реферат generation names the реферат

| Field | Value |
|---|---|
| Description | The failure screen is the one place a hardcoded type is least likely to be noticed and most jarring when it appears. |
| Preconditions | Account A signed in; реферат picked; the provider stub is set to fail so the generation reaches `status: "failed"`. |
| Test data | `generationFailedTitle('referat')`; backend failure message `Не удалось сгенерировать документ. Попробуйте позже.` |
| Steps | 1. Pick `Реферат`, submit the topic.<br>2. Wait until the generation reports `failed`.<br>3. Read the failure heading and the controls beneath it. |
| Expected result | The failure heading reads exactly `Не удалось сгенерировать реферат`; a retry control is present and enabled; the word `доклад` appears nowhere on the screen. |
| Status | Not run |

---

## 4. Wire

### TC-04-UI-4.1 — Picking реферат generates a реферат

| Field | Value |
|---|---|
| Description | The defect this prevents has already happened once in this product: every card generated a доклад because the picked type never reached the request. The card being newly enabled is exactly when it could happen again. |
| Preconditions | Account A signed in; network requests captured. |
| Test data | Card `Реферат` (internal id `referat`), expected wire value `реферат` |
| Steps | 1. Pick `Реферат` in the modal.<br>2. Type the topic and submit.<br>3. Inspect the captured `POST /api/v1/generations` request body. |
| Expected result | The body's `document_type` is exactly `"реферат"` (Cyrillic, from `WIRE_DOCUMENT_TYPE.referat`) — not `"referat"` and not `"доклад"`; the request also carries an `Idempotency-Key` header. |
| Status | Not run |

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
