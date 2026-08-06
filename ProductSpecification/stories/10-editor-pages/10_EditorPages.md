# Editor pages (pagination, page setup, headers/footers)

## Brief Description

The editor stops being an endless scroll and lays the document out on sheets. Page geometry
is per-document (`page_settings`), the user sees which page they are on and how the length
compares to the volume they asked for, and the exports carry the same geometry, headers and
page numbers.

## Flow

1. User opens a document in the editor.
2. Client loads the document with its `page_settings`; a null value reads as the default preset.
3. The editor waits for the bundled document font, then measures content against the page
   box and lays it out on sheets, breaking automatically by height.
4. A counter shows "стр. N из M"; for a document that came from a generation it also shows
   the length against the requested `volume_pages`.
5. User inserts a manual page break (Ctrl+Enter); it is part of the content and survives
   save/reload.
6. User opens page setup and changes sheet size, orientation, margins, font size, line
   height, header/footer text or numbering flags.
7. Client saves the whole settings object via `PUT /documents/{id}` under the document's
   version token; the layout recomputes against the stored result.
8. Export applies the same `page_settings`: PDF and DOCX carry the geometry, the manual
   breaks, and headers/footers with page numbering.

## Acceptance Criteria

### Layout

- Content is laid out on sheets whose box equals the effective geometry; a block that does
  not fit continues on the next sheet. A block whose height exactly equals the remaining
  space **fits on the current page** — the equality case is pinned, not left to rounding.
- A manual page break starts a new sheet, round-trips through save/reload, and passes the
  `HtmlSanitizer` allowlist unchanged.
- Editing above a break re-flows the pages below it; the break stays attached to its
  position in the content, never to a page index.
- Incremental repagination is observably equivalent to a full remeasure: after a scripted
  edit sequence — including an edit above a manual break and a geometry change — the
  incrementally derived page count and break positions equal a from-scratch layout.
- The page counter reflects current content and geometry and updates as the user types; the
  count is derived on read, never stored.
- A document generated with `volume_pages = N` laid out to M pages shows the divergence;
  nothing is regenerated automatically.

### Geometry, units and numeric boundaries

- The realised content box matches the stored settings in each render target's own unit
  (browser CSS px, WeasyPrint mm, DOCX EMU/half-points/twips), verified on a **non-default,
  self-distinct** fixture — A5 landscape, margins 35/15/25/40 mm, 11 pt, line height 1.15 —
  where every value differs from every other and from the preset, so a dropped or doubled
  conversion factor changes the asserted magnitude. `Letter` (imperial-native) is covered,
  not only A4.
- All numeric bounds are **inclusive**; each is asserted at the bound and one step outside.
- Geometry is rejected at the boundary — never clamped, never partially applied — for: a
  negative margin; margins whose sum **equals** the sheet dimension (zero content box); a
  value outside its range; a non-finite or overflowing JSON number; a string where a number
  is required; a font/line-height/margin combination whose content box cannot hold one line
  (otherwise pagination emits pages forever).
- Numbers reach CSS, `@page`, PDF and DOCX XML formatted under an invariant locale — a
  render under a comma-decimal locale produces byte-identical geometry. The Cyrillic counter
  is display-locale text and is exempt.
- Geometry values reach the CSS/`@page` sink as typed numbers emitted by the value object,
  never as interpolated request strings.

### Persistence and contract

- `page_settings` round-trips through save and reload; a never-configured document keeps
  `NULL` and renders on the default preset.
- On `PUT`, an omitted `page_settings` leaves the stored value unchanged, an explicit null
  resets it to the default, and a supplied object **replaces the stored one wholesale** — a
  supplied object omitting `header_text` resets that header to default, it is not merged.
- An unknown key in a supplied `page_settings` is rejected (422), not ignored. A **stored**
  value carrying a key or enum constant this code version does not define is preserved and
  read as that key's default — never a crash, never a silent downgrade of the whole object.
- The persisted JSONB contains exactly the allow-listed keys, re-serialized from the domain
  value object — no request blob is stored verbatim.
- Server-owned fields on `POST`/`PUT` stay ignored (story-5 posture); `page_settings` is the
  only new client-writable field.
- Page settings save through the existing version-guarded CAS
  (`save_content_if_version_matches`): a stale version is rejected and surfaced, never a
  blind overwrite. A `content` save and a `page_settings` save interleaved on one document
  each survive or are explicitly rejected — neither is silently dropped.
- A `PUT` carrying a valid `content` change plus out-of-range geometry is rejected whole:
  the stored `content` is byte-identical to its pre-request value.
- Replaying a byte-identical `PUT` twice leaves `content` + `page_settings` identical to a
  single application.
- Old application code (unaware of the column) still reads **and writes** `Document` after
  the additive column lands: an N-1 save leaves an existing `page_settings` byte-identical,
  never nulled.
- Page settings are owner-scoped through the existing document access path — a foreign or
  absent document is 404, never 403, on read, on write, **and on export**, with an identical
  body in both cases.

### Text, escaping and disclosure

- `header_text` / `footer_text` are NFC-normalized before storing and before length-checking;
  a store→read round-trip is byte-exact. Over-length is rejected, never truncated.
- Header/footer text is stored as plain text and escaped at **every** sink — the editor,
  PDF, DOCX header XML, and log/error output. Markup, control characters and the
  page-number placeholder syntax cannot inject into any of them.
- Header/footer text and page numbers render intact for multibyte content (Cyrillic, emoji,
  combining accent) in all three targets.
- `page_settings` rejection bodies use the sanctioned generic error shape — no stack trace,
  internal class name, JSON-path fragment, or DB message.
- The DOCX metadata redaction survives the headers/footers extension: a sentinel owner value
  appears in neither `docProps` nor the new header/footer XML.

### Fonts, failure and limits

- The bundled document face is validated at startup — missing or unreadable fails fast at
  boot, not as a substitution at first render.
- A face that fails to resolve is a **hard, attributable failure, not a metric
  substitution**: export fails with a stable error rather than returning bytes laid out in a
  fallback, and the editor defers layout until the document face is confirmed loaded, with a
  finite timeout and a defined outcome for load-fails and load-slow.
- No render depends on a system-installed face.
- An export failure in any of {geometry, manual breaks, header/footer, numbering} fails the
  export with an attributable error — never a 200 with an element silently omitted.
- Block count and nesting depth are bounded at the request boundary independently of the
  code-point limit; the deadline cases are asserted against a max-block-count document, a
  max-depth document and a single max-length unbreakable block, not only a 200 000-character
  body.
- Pagination and export of a max-size document complete within their named budgets
  (Validation Rules); on expiry the operation aborts with the sanctioned error and frees its
  thread — no detached render. Story 17's existing render-concurrency bound is not regressed.
- Export output is unchanged for a document with default settings and no manual breaks —
  story 17's shipped export behaviour does not regress.

### Client

- The editor renders the authoritative result of the latest save: with a content save and a
  page-setup save in flight together, a late-arriving earlier response never replaces newer
  state.
- Optimistic repagination rolls back on rejection — a geometry the server refuses leaves the
  editor on its pre-change layout, not merely showing an inline error.
- The page-setup apply and export controls are locked while their request is in flight.
- Un-persisted page-setup edits (header/footer text above all) mark the document dirty and
  fire the existing `beforeunload` guard.

## Validation Rules

| Field | Rule |
|-------|------|
| `page_settings` | optional object; `NULL` = default preset; unknown key → 422; omitted on `PUT` = unchanged, explicit null = reset, supplied = wholesale replace |
| `page_size` | `A4` (210×297 mm), `A5` (148×210 mm), `Letter` (215.9×279.4 mm) |
| `orientation` | `portrait`, `landscape` |
| `margins_mm` | four numbers (top/right/bottom/left) in mm; each ≥ 0; must leave a content box of non-zero width and height that fits at least one line |
| `font_size_pt` | 8–72 inclusive, in points |
| `line_height` | 1.0–3.0 inclusive, unitless multiplier |
| `header_text` / `footer_text` | optional plain text, ≤ 200 code points (NFC), no markup |
| `show_page_numbers` | boolean, default true |
| `skip_number_on_first_page` | boolean, default true |
| content | story-5 rules unchanged (block HTML, 200 000 code points) **plus** ≤ 5 000 blocks and ≤ 10 levels of nesting |
| Budgets | initial pagination of a max-size document ≤ 2 s; incremental recompute ≤ 150 ms; export within story 17's configured render deadline |

## Screen States

- **Editor, paginated** — the document on sheets, page gaps visible.
- **Measuring / font pending** — a defined state while the face loads and before a page
  count exists; distinguishable from an error and from empty.
- **Page setup panel** — all fields, per-field boundary errors inline.
- **Page-setup save failed** — non-validation failure (network, 5xx) with retry, distinct
  from inline 422 errors.
- **Page counter** — "стр. N из M", plus the requested-volume comparison where present.
- **Manual break** — a visible marker in the flow, selectable and deletable.
- **Empty document** — one blank sheet, not a spinner.

## Core Requirements

- Build order: `page_settings` (column, domain value object, API contract) → editor
  pagination → page counter → manual page break → headers/footers. Pagination against
  hardcoded constants would be rewritten, along with its tests, once settings land.
- `page_settings` is a JSONB column on `Document`; bounds live in a domain value object, not
  the DB. `NULL` reads as the default preset — no data migration.
- Settings writes reuse the existing version-guarded CAS rather than a new mechanism.
- The manual page break is one new editor node and one new `HtmlSanitizer` allowlist entry.
  Coordinate the allowlist change with story 5's paste-sanitize scenario.
- The document font is **Liberation Serif**, bundled as a webfont, byte-identical on both
  sides. Font choice is not a setting (known-debt #15).
- The PDF engine stays WeasyPrint. Editor↔PDF page equality is **not** claimed and must not
  be asserted by any test in this story (known-debt #14); the divergence is measured once
  pagination ships and the engine decision follows those numbers.
- DOCX carries geometry, manual breaks and headers/footers best-effort — Word repaginates on
  open, so no scenario may assert DOCX page equality with the editor.
- `DocumentRenderer` gains the page settings in its signature; `FormatDispatchingRenderer`
  and the export usecase are otherwise unchanged. Export stays synchronous — no queue.
- Pagination recomputes incrementally from the changed block onward; the per-block
  measurement cache is bounded and evicts, or it grows to the document's block cardinality
  over a session.
