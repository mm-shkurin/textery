<!-- COPIED FILE. Source of truth: ProductSpecification/stories/10-editor-pages/tests/extended/06_Integration_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Editor pages — Integration Tests (Extended)

Seams: the two render libraries' unit conversions across every supported sheet, the
determinism of repeated renders, and the round-trip of a manual break through the
sanitizer, the database and both exporters.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.pages@textery.test` / `Qa!Pages2026` |
| Document A2 (configured) | id `c31f8a05-6d47-4b92-8e10-2f5c9d7b3a64`, settings `S1` |
| Settings `S1` | A5, landscape, margins 35/15/25/40 mm, 11 pt, line height 1.15, header `Кафедра ИВТ`, footer `Текстери`, numbering on |
| Sheet dimensions | A4 210 × 297 mm (11906 × 16838 tw), A5 148 × 210 mm (8391 × 11906 tw), Letter 215.9 × 279.4 mm (12240 × 15840 tw) |
| Landscape rule | width and height swap; the twip pairs swap with them and `w:orient="landscape"` is emitted |
| Break markup | `<div data-page-break="true"></div>`, allow-listed in `HtmlSanitizer` |
| Legacy document A23 | id `0f6b81d4-7a3e-42c5-9b08-e15d739ca6b2`, created before this story, `page_settings` `NULL`, no manual break |
| Pre-story reference | stored fixtures `story17_reference.pdf` / `story17_reference.docx` for document A23's content |

## 1. Geometry Across Targets

### TC-10-INT-1.1 — Every supported sheet size and orientation renders at its declared dimensions

| Field | Value |
|---|---|
| Description | Three sheets in two orientations are six conversions; a single wrong factor or an unswapped landscape pair hides behind the one combination the default preset exercises. |
| Preconditions | Six documents exist, owned by account A, identical but for `page_size` and `orientation`, each with margins 20/15/20/30 mm, 12 pt, line height 1.2. |
| Test data | A4 portrait 210 × 297 / landscape 297 × 210; A5 portrait 148 × 210 / landscape 210 × 148; Letter portrait 215.9 × 279.4 / landscape 279.4 × 215.9; twips as in the shared table, swapped for landscape |
| Steps | 1. Export each of the six documents as `pdf` and read `/MediaBox` in mm.<br>2. Export each as `docx` and read `w:pgSz` (`w:w`, `w:h`, `w:orient`) from `word/document.xml`. |
| Expected result | Each PDF's `/MediaBox` equals its declared millimetre pair within 0.5 mm — including `215.9 × 279.4` for Letter, which is not rounded to 216 × 279. Each DOCX carries the matching twip pair (A4 `11906 × 16838`, A5 `8391 × 11906`, Letter `12240 × 15840`, swapped in landscape) and `w:orient="landscape"` on exactly the three landscape documents. |
| Status | Not run |

### TC-10-INT-1.2 — The same settings render identically on repeated exports

| Field | Value |
|---|---|
| Description | A render that varies between runs — through hash ordering, a float path or an ambient value — makes every geometry assertion in this suite intermittently false. |
| Preconditions | Document A2 exists with settings `S1` and is not modified between the two exports. |
| Test data | Document A2, both formats, exported twice with a 60 s gap; fields expected to differ: `/CreationDate` and `/ModDate` in the PDF, `dcterms:created` / `dcterms:modified` in `docProps/core.xml` |
| Steps | 1. Export document A2 as `pdf` twice and as `docx` twice.<br>2. Compare each PDF pair on `/MediaBox`, page count, per-page text and text-frame geometry.<br>3. Compare each DOCX pair on `w:pgSz`, `w:pgMar`, `w:sz`, `w:spacing` and `word/document.xml` body content.<br>4. Diff the two files of each pair byte for byte and list every differing region. |
| Expected result | Every geometry value compared in steps 2–3 is identical between runs and the page counts match. Step 4: the only byte differences fall inside the timestamp fields named above — no geometry, text or structural bytes differ. |
| Status | Not run |

---

## 2. Content Round-Trip

### TC-10-INT-2.1 — A manual break survives a full save, reload and export cycle

| Field | Value |
|---|---|
| Description | The break is one new sanitizer allow-list entry; if it is stripped at any hop the document silently loses a page boundary the user placed deliberately. |
| Preconditions | Document A24 exists, owned by account A, containing one manual break; `HtmlSanitizer` allow-lists `div[data-page-break]`. |
| Test data | Document A24 id `85be2f30-6d9a-4c17-a4f2-b0937e5cd614`, content `<p>До разрыва.</p><div data-page-break="true"></div><p>После разрыва.</p>` |
| Steps | 1. `PUT` document A24 with that content and the current `version`; read the response `content`.<br>2. Read the `content` column of the row directly from the DB.<br>3. `GET` document A24 and read `content`.<br>4. Open the editor and confirm the break marker renders between the two paragraphs.<br>5. Export as `pdf` and as `docx`. |
| Expected result | At steps 1, 2 and 3 the content is byte-identical to the submission — `<div data-page-break="true"></div>` is present with its attribute intact, neither stripped nor rewritten by the sanitizer, and always between the same two paragraphs. Step 4: the marker renders at that position. Step 5: the PDF starts a new page at the break and the DOCX carries `<w:br w:type="page"/>` there. |
| Status | Not run |

### TC-10-INT-2.2 — A legacy document with no breaks and no settings exports unchanged

| Field | Value |
|---|---|
| Description | The regression guard for every document that predates this story: opening and saving it must not quietly configure it or change a byte of its output. |
| Preconditions | Document A23 exists, created before this story, `page_settings` `NULL`, no manual break; the pre-story reference exports are stored. |
| Test data | Document A23 id `0f6b81d4-7a3e-42c5-9b08-e15d739ca6b2`; save body = the identical content with the current `version` and no `page_settings` key |
| Steps | 1. `GET` document A23 and hash `content`.<br>2. `PUT` the identical content back, omitting `page_settings`.<br>3. `GET` document A23 and re-hash; read the `page_settings` column directly.<br>4. Export as `pdf` and as `docx` and compare with the stored pre-story references. |
| Expected result | Step 3: the content hash equals step 1 and the `page_settings` column is still SQL `NULL` — the save did not materialize a preset. Step 4: the PDF matches the reference on page count, `/MediaBox` and extracted text; the DOCX matches on `w:sectPr` and body XML, ignoring only render timestamps; neither file carries a header or footer part. |
| Status | Not run |

---

## 3. Multibyte

### TC-10-INT-3.1 — Header, footer and page numbers survive multibyte content into both formats

| Field | Value |
|---|---|
| Description | Mojibake and tofu boxes are the failure: the bundled face and the encoding path must carry every character the panel accepts, in the header band as well as the body. |
| Preconditions | Document A25 exists, owned by account A, laid out to at least 2 pages, numbering on with the first page skipped. |
| Test data | Document A25 id `d4207ec8-935f-41b6-8a70-c62e5b03971d`; content `<p>Привет, мир.</p>`; `header_text` `Отчёт 🎓`; `footer_text` `e` + U+0301 + ` — Текстери` (NFC `é — Текстери`) |
| Steps | 1. `PUT` document A25 with that header, footer and content.<br>2. Export as `pdf`; extract the text layer of each page including the header and footer bands.<br>3. Export as `docx`; read `word/document.xml`, `word/header1.xml` and `word/footer1.xml`.<br>4. Grep both extractions for `?` and U+FFFD, and inspect the rendered PDF for empty tofu boxes. |
| Expected result | The PDF's page 2 carries `Отчёт 🎓` in its header band, `é — Текстери` in its footer band, and the folio `2`; page 1 carries the header and footer but no folio. The DOCX header and footer parts carry the same strings as submitted in NFC. Step 4 finds zero `?` substitutions, zero U+FFFD and no tofu box in either target. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the declared millimetre values` | A4 210×297, A5 148×210, Letter 215.9×279.4 |
| `fields expected to differ between renders` | Timestamps written by the render library |
| `the pre-story output` | A stored reference file produced before page settings existed |
