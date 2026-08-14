<!-- COPIED FILE. Source of truth: ProductSpecification/stories/10-editor-pages/tests/06_Integration_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Editor pages — Integration Tests

Story 10 calls no external HTTP service. Its integration seams are the two render
libraries and the font asset — the places where a value crosses out of the application's
own types into someone else's engine, and where a unit conversion or an unpinned ambient
silently changes the result.

---

## 1. Geometry Across the Render Boundaries

### 1.1 The realised page geometry matches the settings in every target
```gherkin
Given a document whose page settings are self-distinct in every field
When it is laid out in the editor, exported as pdf, and exported as docx
Then each target's realised content box matches the settings in that target's own unit
And an imperial sheet size is covered alongside the metric ones
```

Every value in the fixture differs from every other and from the default preset — the
default is the one fixture that passes with all three conversions broken, because each
side is likely to have it hardcoded.

### 1.2 Numbers are formatted under an invariant locale
```gherkin
Given a document with a fractional line height and fractional margins
When it is exported under a locale whose decimal separator is a comma
Then the resulting geometry is identical to the same export under the default locale
```

Catches the silent failure where a comma-decimal number becomes an invalid stylesheet
declaration, is dropped, and the document simply paginates differently with no error.

---

## 2. Render Library Behaviour

### 2.1 The PDF renderer honours manual breaks, headers and numbering
```gherkin
Given a document with a manual page break, a header, a footer and numbering enabled
When it is exported as pdf
Then the content after the break begins a new page
And the header and footer appear on the pages where they are configured to appear
And the first page carries no number while later pages do
```

### 2.2 The DOCX renderer emits breaks, headers and section geometry
```gherkin
Given the same document
When it is exported as docx
Then the file carries an explicit page break at that position
And carries header and footer parts with page numbering
And its section geometry matches the page settings
And no assertion is made about where its pages end
```

The final line is deliberate: Word repaginates on open, so page-end equality is
unreachable for DOCX by any implementation and must not be asserted.

---

## 3. Font Resolution

### 3.1 A resolvable font renders without touching the network
```gherkin
Given the bundled document font is present
When a document is exported
Then the render completes using that face
And no outbound network request is made during the render
```

### 3.2 An unresolvable font fails the render instead of substituting
```gherkin
Given the bundled document font cannot be resolved at render time
When a document is exported
Then the export fails with the sanctioned error
And no file is produced
And an attributable server-side signal is emitted for the document
```

The render library catches per-resource fetch failures and continues, so without this
guard a missing face yields a successful export in substituted metrics.

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `self-distinct in every field` | A5 landscape, margins 35/15/25/40 mm, 11 pt, line height 1.15 |
| `that target's own unit` | CSS px in the browser, mm in the PDF, EMU / half-points / twips in the DOCX |
| `an imperial sheet size` | `Letter` (215.9 × 279.4 mm) |
| `the default locale` | The application's pinned invariant formatting locale |
| `an attributable server-side signal` | Log/metric keyed by document id, distinct from the happy path |
| `no outbound network request` | Observed against a fake network, as in story 17's SSRF guard |
