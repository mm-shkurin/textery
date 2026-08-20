> These are additional edge case tests. Implement after core tests pass.

# Editor pages — UI Tests (Extended)

Screen: the document editor at `/documents/{id}`, its page-setup panel, page rail and the
narrow-viewport page strip.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.pages@textery.test` / `Qa!Pages2026` |
| Document A8 (3 pages, generated) | id `3b7e60f4-2c19-4d5a-91b8-cf40a2e75d16`, `volume_pages` requested `5`, laid out to `3` |
| Document A2 (configured) | id `c31f8a05-6d47-4b92-8e10-2f5c9d7b3a64`, settings `S1` |
| Settings `S1` | A5, landscape, margins 35/15/25/40 mm, 11 pt, line height 1.15, header `Кафедра ИВТ`, footer `Текстери`, numbering on, skip-first off |
| Default preset | A4, portrait, margins 20/15/20/30 mm, 14 pt, line height 1.5, numbering on, skip-first on |
| Counter text | `стр. N из M` in the editor status bar |
| Volume comparison text | `запрошено 5 стр.` next to the counter |
| Sheet selector | `[data-testid="page-sheet"]`; folio `[data-testid="page-folio"]`; strip chip `[data-testid="page-chip-N"]` |
| Panel controls | `Применить`, `Отмена`, `Сбросить`, `Нумерация страниц`, `Не нумеровать первую страницу` |
| Narrow viewport | 390 × 844 px (mobile), keyboard inset 300 px |

## 1. Layout Edges

### TC-10-UI-1.1 — A block taller than a page does not vanish

| Field | Value |
|---|---|
| Description | A layout that only moves whole blocks to the next sheet has nowhere to put a block that fits on no sheet — the usual outcome is a clipped or dropped block. |
| Preconditions | Account A signed in; document A17 exists whose content is a single `<p>` of ~12 000 characters, taller than one A4 page at the default preset. |
| Test data | Document A17 id `9e3c1f47-a25b-4680-bd39-7c04f1a8e2b5`; first sentence `Начало длинного блока.`; last sentence `Конец длинного блока.` |
| Steps | 1. Open `/documents/9e3c1f47-a25b-4680-bd39-7c04f1a8e2b5` and wait for the counter.<br>2. Count the sheets and read the text rendered on each.<br>3. Concatenate the per-sheet text and compare with the stored content. |
| Expected result | At least 2 sheets are rendered; `Начало длинного блока.` appears on sheet 1 and `Конец длинного блока.` on the last sheet; the concatenated text equals the stored content exactly — no characters are clipped at a sheet boundary and none is duplicated across one. |
| Status | Not run |

### TC-10-UI-1.2 — A block whose height exactly fills the remaining space stays on the page

| Field | Value |
|---|---|
| Description | The equality case is pinned, not left to rounding: a `>=` where a `>` belongs pushes the block to the next sheet and leaves a half-empty page followed by an empty one. |
| Preconditions | Document A18 exists whose final block is measured to be exactly the remaining height of sheet 1 at the default preset. |
| Test data | Document A18 id `6a48e2d0-b71c-4359-8f2e-04d95c37be18`; remaining space on sheet 1 and the block height both `120.0 px` (assert equal to within 0.01 px before running) |
| Steps | 1. Open document A18 and wait for the layout.<br>2. Confirm the measured block height equals the remaining space on sheet 1.<br>3. Read which sheet the block is rendered on and count the sheets. |
| Expected result | The block is rendered on sheet 1, not sheet 2; the total sheet count equals 1 (no empty sheet is produced after it) and the counter reads `стр. 1 из 1`. |
| Status | Not run |

### TC-10-UI-1.3 — Deleting content removes the trailing sheet

| Field | Value |
|---|---|
| Description | Repagination that only grows leaves ghost sheets behind after a deletion, and the counter then reports a document longer than it is. |
| Preconditions | Document A8 open, laid out to 3 pages, font resolved. |
| Test data | Select from the middle of sheet 2 to the end of the document and press `Delete` — enough removal to fit 2 pages |
| Steps | 1. Open document A8 and read the counter and sheet count.<br>2. Select the trailing content and delete it.<br>3. After the recompute, read the counter and count the sheets. |
| Expected result | Step 1: 3 sheets, `стр. 1 из 3`. Step 3: exactly 2 sheet elements remain in the DOM — the third is removed, not merely emptied — and the counter reads `стр. N из 2`. |
| Status | Not run |

### TC-10-UI-1.4 — A long unbreakable word does not overflow the sheet

| Field | Value |
|---|---|
| Description | A word wider than the content box either breaks or overflows; overflowing draws text into the margin and off the sheet, where the export cannot follow. |
| Preconditions | Document A19 exists containing one paragraph with a single 400-character run of Cyrillic letters and no spaces. |
| Test data | Document A19 id `b3d17f52-8ca0-46e9-9d74-2f5081cb63a7`; content box width at the default preset 165 mm ≈ 623.6 px |
| Steps | 1. Open document A19 and wait for the layout.<br>2. Measure the paragraph's rendered bounding box.<br>3. Compare it with the sheet's content box. |
| Expected result | The paragraph's right edge is at or inside the content box's right edge (≤ 623.6 px wide, within 1 px); no text is painted in the margin or outside the sheet element; the sheet has no horizontal scrollbar. |
| Status | Not run |

---

## 2. Page Setup Panel Edges

### TC-10-UI-2.1 — Cancelling discards the entered values

| Field | Value |
|---|---|
| Description | A cancel that leaves the typed values in the form makes the next open look like saved state and invites an accidental apply. |
| Preconditions | Document A2 open with settings `S1`; panel open. |
| Test data | Modified in the panel: `page_size` → `A4`, `font_size_pt` → `20`, header → `Черновик`; then `Отмена` |
| Steps | 1. Enter the modified values in the panel.<br>2. Press `Отмена`.<br>3. Read the rendered sheet geometry and the counter.<br>4. Reopen the panel and read every field. |
| Expected result | Step 2: the panel closes and no `PUT` is issued. Step 3: the sheets are still at A5 landscape, 11 pt — the pre-edit geometry. Step 4: the fields show `A5`, `11`, header `Кафедра ИВТ` — the saved values, not `A4`, `20`, `Черновик`. |
| Status | Not run |

### TC-10-UI-2.2 — Resetting asks before discarding a configured setup

| Field | Value |
|---|---|
| Description | Reset is a one-click wipe of a header, a footer and eight geometry values with no undo — it must be confirmed. |
| Preconditions | Document A2 open with settings `S1` (header, footer and non-default geometry all set); panel open. |
| Test data | The `Сбросить` control; confirmation dialog with `Сбросить` / `Отмена` |
| Steps | 1. Press `Сбросить`.<br>2. Read what is displayed before anything changes.<br>3. Dismiss the confirmation with `Отмена` and read the panel fields and the `PUT` traffic.<br>4. Press `Сбросить` again and confirm. |
| Expected result | Step 2: a confirmation dialog appears naming what will be discarded; no `PUT` has been issued yet. Step 3: the panel still shows `S1` and no request was sent. Step 4: a `PUT` with `page_settings: null` is issued and answers `200 OK`; the sheets redraw at the default preset. |
| Status | Not run |

### TC-10-UI-2.3 — Turning numbering off removes the folios

| Field | Value |
|---|---|
| Description | The flag has to reach the layout, not only the stored object — a folio that survives the setting is visible on every printed page. |
| Preconditions | Document A8 open, 3 pages, numbering currently on and folios visible on sheets 2 and 3. |
| Test data | `Нумерация страниц` unchecked, then `Применить` |
| Steps | 1. Confirm folios are present on sheets 2 and 3.<br>2. Uncheck `Нумерация страниц` and press `Применить`.<br>3. After the save, inspect every sheet for a folio element. |
| Expected result | The `PUT` answers `200 OK` with `show_page_numbers: false`; zero `[data-testid="page-folio"]` elements remain in the DOM on any sheet — no folio is merely hidden by CSS while still occupying its band. |
| Status | Not run |

### TC-10-UI-2.4 — Turning off the first-page exception numbers the first page

| Field | Value |
|---|---|
| Description | The two numbering flags interact; clearing the exception must number sheet 1 as `1` without restarting the sequence on the later sheets. |
| Preconditions | Document A8 open, 3 pages, numbering on and `skip_number_on_first_page` on (sheet 1 has no folio). |
| Test data | `Не нумеровать первую страницу` unchecked, then `Применить` |
| Steps | 1. Confirm sheet 1 has no folio and sheets 2 and 3 show `2` and `3`.<br>2. Uncheck `Не нумеровать первую страницу` and press `Применить`.<br>3. Read the folio on each of the three sheets. |
| Expected result | The `PUT` answers `200 OK` with `skip_number_on_first_page: false`; the sheets now show `1`, `2` and `3` in order — sheet 1 gains its folio and the later folios keep the numbers they had. |
| Status | Not run |

---

## 3. Counter Edges

### TC-10-UI-3.1 — A document matching its requested volume shows no shortfall

| Field | Value |
|---|---|
| Description | An off-by-one comparison flags a document that met its target, teaching the user to ignore the indicator. |
| Preconditions | Document A20 exists, generated with `volume_pages = 3`, and lays out to exactly 3 pages. |
| Test data | Document A20 id `4d17e58b-0f6a-4c23-91be-83a05c7d6f14`, requested `3`, actual `3` |
| Steps | 1. Open document A20 and wait for the layout.<br>2. Read the status bar in full. |
| Expected result | The status bar shows `стр. 1 из 3` only; no `запрошено` text and no shortfall indicator element is present in the DOM. |
| Status | Not run |

### TC-10-UI-3.2 — A document longer than requested is not reported as a shortfall

| Field | Value |
|---|---|
| Description | A comparison on absolute difference rather than direction reports "too short" for a document that is too long — the opposite of the truth. |
| Preconditions | Document A21 exists, generated with `volume_pages = 3`, and lays out to 5 pages. |
| Test data | Document A21 id `e81b6094-c352-4a7f-b0d6-25f39ac47e10`, requested `3`, actual `5` |
| Steps | 1. Open document A21 and wait for the layout.<br>2. Read the status bar and any comparison text. |
| Expected result | The counter reads `стр. 1 из 5`; no shortfall wording (`не хватает`, `меньше`) appears anywhere; if a comparison is shown at all it states the requested `3` neutrally and never claims the document is short. |
| Status | Not run |

### TC-10-UI-3.3 — A manually created document shows no volume comparison

| Field | Value |
|---|---|
| Description | A manual document has no requested volume; a comparison against a missing value renders as `из null` or against a default nobody chose. |
| Preconditions | Document A1 exists, created manually (never generated, no `volume_pages`). |
| Test data | Document A1 id `9d4b1e7a-3c62-4f08-b5d1-8e2a70c4f159` |
| Steps | 1. Open `/documents/9d4b1e7a-3c62-4f08-b5d1-8e2a70c4f159` and wait for the layout.<br>2. Read the status bar in full. |
| Expected result | The status bar shows only `стр. 1 из 1`; no `запрошено` text, no comparison element, and no `null`, `undefined` or `0` appears in the status bar. |
| Status | Not run |

---

## 4. Mobile

### TC-10-UI-4.1 — The page strip scrolls to the current page

| Field | Value |
|---|---|
| Description | On a narrow viewport only a few chips fit; a strip that never scrolls leaves the current page marked somewhere the user cannot see. |
| Preconditions | Account A signed in on a 390 × 844 px viewport; document A22 exists laying out to 12 pages. |
| Test data | Document A22 id `7c05a9e3-64b1-4f28-8d0a-b3e9174c52d6`; caret moved to page 9; chip selector `[data-testid="page-chip-9"]` |
| Steps | 1. Open document A22 at 390 × 844 px and note which chips are visible.<br>2. Move the caret to a paragraph on page 9.<br>3. Read the strip's scroll position and the bounding box of chip 9. |
| Expected result | Chip 9 is fully inside the strip's visible box after the caret move (its left and right edges are within the strip's client rect); it carries the current marking (`aria-current="page"`); the counter reads `стр. 9 из 12`. |
| Status | Not run |

### TC-10-UI-4.2 — The setup sheet does not obscure the field being edited

| Field | Value |
|---|---|
| Description | The on-screen keyboard eats the bottom third of the viewport; a bottom sheet that does not react hides exactly the field the user just focused. |
| Preconditions | Account A signed in on a 390 × 844 px viewport with document A8 open; the page setup bottom sheet is open. |
| Test data | The footer text input (the lowest field in the sheet); simulated keyboard inset 300 px |
| Steps | 1. Open the page setup bottom sheet.<br>2. Focus the footer text input.<br>3. Apply the 300 px keyboard inset and read the input's bounding box against the remaining visible viewport. |
| Expected result | The focused input's bounding box lies entirely above the keyboard inset (its bottom edge ≤ 544 px) and is fully within the visible viewport; the sheet scrolls or resizes rather than leaving the field behind the keyboard. |
| Status | Not run |
