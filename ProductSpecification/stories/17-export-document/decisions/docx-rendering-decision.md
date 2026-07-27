# Decision: DOCX rendering strategy and metadata redaction

**Date**: 2026-07-27 **Scenarios**: 2.2 (with seams into 3.4, 4.1, 4.2, 4.5, Load 2.1, Infra 1.1/2.1, Security 5.1)

Why: WeasyPrint renders PDF only, so the DOCX branch of the unified `DocumentRenderer` port needs its own engine — and the chosen engine's defaults leak server identity/time into the file, which forces both a library and a redaction decision.

| Rejected | Why |
|----------|-----|
| pandoc via subprocess | Ships an external binary (boot-dependency hazard fires hard — Infra 1.1), subprocess adds a resource/temp-file leak surface, and gives weak control over `docProps` metadata. |
| python-docx only (no HTML parse) | Full metadata control and fewest deps, but drops the stored content's HTML formatting (bold, lists, headings) → a materially poorer document than the PDF export. |

**Chosen**: A format-dispatching renderer implementing the existing `DocumentRenderer` port, routing PDF→`WeasyPrintPdfRenderer`, DOCX→a new pure-Python `HtmlDocxRenderer` (`htmldocx` parsing the already-sanitized HTML into a `python-docx` `Document`). Pure-Python (no native binary, so nothing new to fail-fast at boot beyond the pip deps), no network (SSRF-safe by construction), and `python-docx` exposes `core_properties` so the renderer can set neutral metadata instead of library defaults.

## Model

- New adapter `backend/adapters/rendering/src/rendering/format_dispatching_renderer.py` — `FormatDispatchingRenderer` implements `DocumentRenderer`, holds `{PDF: WeasyPrintPdfRenderer, DOCX: HtmlDocxRenderer}`, dispatches `render(content, export_format)` on the enum. Raises loudly on an unmapped member (no silent wrong-format bytes).
- New adapter `HtmlDocxRenderer.render(content, ExportFormat.DOCX) -> bytes` — `htmldocx` → `python-docx` Document → `BytesIO`; sets neutral `core_properties` (no OS username as author, `created`/`modified` from an injected clock, not raw system time).
- Usecase `ExportDocument`: add `ExportFormat.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document"` to `_MEDIA_TYPE`; move the `_MEDIA_TYPE[export_format]` lookup **ahead of** `render()` so an unmapped format fails fast before any wasted render (closes the docx-passes-validation-then-KeyErrors→500 window).
- Composition root wires `FormatDispatchingRenderer` in place of the bare `WeasyPrintPdfRenderer`.
- Deps: add `htmldocx` + `python-docx` to backend requirements (and CI). No new native OS libs.

## Edge Cases

| Case | Behavior |
|------|----------|
| `format=docx` on an owned document | Renders DOCX, returns `RenderedExport(docx_bytes, wordprocessingml)`. |
| Unmapped `ExportFormat` member (future format added without a `_MEDIA_TYPE` entry) | Fail-fast at the media lookup before render; red-usecase adds an exhaustiveness test so this can never silently 500. |
| DOCX `docProps` metadata | Neutral core properties; no OS/process username, no raw server wall-clock — guarded so the downloaded file leaks no server identity/time (unowned GAP from the group-07 hazard scan, assigned here). |
| Absent / foreign document | Owner-scoped fetch → None → 404, unchanged from Sc 2.1 (never reaches render). |
