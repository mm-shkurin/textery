# Story 10 — Interview (Editor pages / pagination)

Interviewed 2026-08-01. Branch `features/story-10-editor-pages`. Both layers, one session.

**The backlog row is mis-named.** `stories.md` calls story 10 "Text Editor polish
(formatting, autosave)" — but formatting, autosave, title, undo/redo, paste-sanitize,
word count and tables all belong to story 5's `editor-extension.md` (scenarios E3–E8,
partly unshipped). Story 10 is **pages**: the editor stops being an endless scroll and
lays the document out on sheets.

ACTION: rename the story-10 row in `ProductSpecification/stories.md` to
"Editor pages (pagination, page setup, headers/footers)" when promoting it out of Backlog.

## Scope

1. **Page setup** — `page_settings` on `Document`: sheet size + orientation, margins,
   font size, line height, header/footer content. Built **first** (see build order).
2. **Pagination in the editor** — content laid out on sheets, automatic breaks by height,
   driven by the stored settings.
3. **Page counter** — "стр. N из M", plus the divergence against the requested
   `volume_pages` ("3 из запрошенных 5").
4. **Manual page break** — user-inserted (Ctrl+Enter), stored in `content`.
5. **Headers / footers + page numbering** — on screen and in both exports.

Out of scope: story 5's E3–E8 (they stay story 5's); font choice as a setting
(known-debt #15); replacing the PDF engine (known-debt #14); columns; per-section page
setup; footnotes; a print preview separate from the editor (the editor *is* the preview).

## Key Architectural Decisions

### DECISION: build order is page_settings → pagination → counter → manual break → headers/footers

Settings first, deliberately, even though the first user-visible result arrives later:
pagination that reads a hardcoded ГОСТ constant would have to be rewritten the moment
settings land, and every pagination test written against constants would be rewritten
with it. The DB column, the domain value object and the API contract are the foundation
both layers stand on.

### DECISION: page settings live in a `page_settings` JSONB column on `Document`

One migration, and adding a key later costs no schema change. Bounds are validated by a
domain value object, not by the DB — the DB is storage, the domain owns rules. Not stored
inside `content`: settings would then pass through `HtmlSanitizer` as user HTML, with weak
validation and a substitution risk.

### DECISION: legacy documents default on read; no data migration

`page_settings IS NULL` reads as the ГОСТ preset. Existing documents open unchanged. A row
is written only when the user actually changes something. Avoids a write-to-every-row
migration and avoids freezing today's default into old data.

### DECISION: the PDF engine is NOT replaced in this story — deferred as known-debt #14

The WYSIWYG requirement ("an editor page must hold the same text as that PDF page") cannot
hold while the editor is laid out by the user's browser and the PDF by WeasyPrint — two
independent engines whose line-breaking drift accumulates down the document. The fix
(headless Chromium via Playwright, one engine on both sides) was costed and deferred:
until pagination exists there is nothing to compare, and the divergence on a typical 5–10
page реферат may be zero, in which case a working renderer would be replaced for nothing.

ACTION after pagination ships: **measure** — same document, editor page boundaries vs.
exported PDF page boundaries, at several lengths — then decide on the numbers.

ACTION meanwhile: do **not** write an acceptance test asserting editor/PDF page equality.
It would encode a guarantee the system does not currently make.

### DECISION: WeasyPrint's SSRF posture is a constraint on any future swap

`_blocked_url_fetcher` refuses every outbound fetch during a render, because the document
HTML is user-controlled. It is WeasyPrint-specific and has no Chromium equivalent;
Chromium's surface is strictly larger (it also executes scripts). Recorded here so the
swap, if it happens, treats the guard as a security scenario in its own right rather than
a detail of a green step.

### DECISION: one bundled font — Liberation Serif — font choice deferred to known-debt #15

The editor and the renderer must draw with the byte-identical font file or page geometry
diverges; a Linux container has no Times New Roman and would silently substitute different
metrics. Times New Roman is Monotype's and cannot be embedded. Liberation Serif (SIL OFL)
is metrically compatible with Times and carries full Cyrillic — the document keeps its
Word page count while staying legally shippable. Shipped as a webfont in the repo, used by
both the editor's `@font-face` and the export path.

### DECISION: page numbering skips the first page by default

ГОСТ behaviour for учебные работы — the title page counts as page 1 but prints no number.
A `skip_number_on_first_page` flag in the header/footer settings, defaulting to on.

### DECISION: DOCX is best-effort and the spec says so

Word repaginates on open, so page equality with DOCX is unreachable by any route — a
property of the format, not a gap. DOCX gets explicit page breaks, headers/footers with
numbering, and the page setup (size, orientation, margins) — all `python-docx` supports.
Pages will *start* where the user put a break but may *end* elsewhere.

ACTION: state this in the story's acceptance criteria, so no later scenario asserts DOCX
page equality.

## Business Rules & Constraints

| Rule | Value |
|------|-------|
| Default preset | A4 portrait, margins 20/10/20/30 mm (top/right/bottom/left), Liberation Serif 14 pt, line height 1.5, page number bottom-centre, not printed on page 1 |
| Sheet sizes | A4, A5, Letter |
| Orientation | portrait, landscape |
| Margins | bounded — each ≥ 0 and small enough to leave a non-empty content box; rejected at the boundary, never silently clamped |
| Font size | bounded range (e.g. 8–72 pt) |
| Line height | bounded range (e.g. 1.0–3.0) |
| Header/footer text | bounded length, sanitized, plain text plus a page-number placeholder |
| `page_settings` | optional; `NULL` = default preset; unknown keys rejected, not ignored |
| Page count | derived, never stored — a stored count goes stale against any edit |
| `volume_pages` divergence | shown, never acted on — no auto-regeneration |

## NOT Yet Implemented (Gaps)

- Nothing in the editor knows about pages. Tiptap runs a plain `block+` document
  (`useManualEditorInstance.ts`) in a continuous scroll.
- No page-break node; `HtmlSanitizer`'s allowlist has no entry for one.
- No `page_settings` column, no domain value object, no API contract for it.
- `POST`/`PUT /documents/{id}` carry no page settings.
- DOCX renderer emits no breaks, headers or footers.
- No embedded fonts anywhere in the repo.

## ALREADY IMPLEMENTED (REUSE)

- Tiptap v3 on a real `block+` schema — paragraphs, H1–H3, lists, blockquote, code block,
  horizontal rule, `TextAlign` as a block attribute (story 5's block-schema ADR).
- `DocumentRenderer` port + `FormatDispatchingRenderer` — page settings reach the
  renderers through them; the port signature gains the settings, nothing else changes.
- `WeasyPrintPdfRenderer` (kept) and `HtmlDocxRenderer` with metadata redaction (extended).
- Document save/load path, `title` (story 5 E4), export download (story 17).
- `volume_pages` on `Generation` — already collected, already sent to GigaChat
  (`gigachat_provider.py:115`); story 10 is the first thing to *check* it.

## Cross-Story Dependencies

- **Story 17 (export)** — soft, now that the engine swap is deferred. Story 10 extends the
  renderers (page setup, breaks, headers/footers) without replacing them, so 17's shipped
  scenarios stay valid. It becomes hard if known-debt #14 is picked up.
- **Story 5 (manual mode)** — shares the editor and the `HtmlSanitizer` allowlist. E3–E8
  remain story 5's. Coordinate the allowlist change (page break) with whoever holds the
  paste-sanitize scenario E5.1.
- **Story 1 / 18 (generation)** — supply `volume_pages`; the divergence indicator reads it.
  No change owed by them.

## Testing Considerations

- Pagination is measured in the browser, so its real coverage is Selenium, not jsdom —
  jsdom has no layout and reports every element as zero-height. Unit tests can cover the
  settings value object and the break-decision logic given *supplied* heights; the actual
  "does it break in the right place" assertion has to run in a real browser.
- Page-setup boundary rules (margins that leave no content box, out-of-range font size)
  are backend domain tests plus a client-side guard — the story-5 posture of surfacing a
  server rejection rather than silently clamping.
- No editor↔PDF equality test — see known-debt #14.

## Performance

Pagination recomputes on every edit and is the first thing in the editor whose cost scales
with document length. A 50-page document remeasured on each keystroke would make typing
stutter; incremental recomputation (only from the changed block onward) is likely needed —
flag for `/story` as a design point, with a measurement before optimising.
