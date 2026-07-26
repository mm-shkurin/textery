# Export document to PDF / DOCX

## Brief Description

An authenticated user downloads a document as PDF or DOCX. The backend renders the file
on the fly from the document's stored sanitized HTML and streams it — nothing is written
to disk.

## Flow

1. User opens a document in the editor and triggers Export, choosing PDF or DOCX.
2. Client calls `GET /documents/{id}/export?format=pdf|docx` with the Bearer token.
3. Backend loads the caller-owned document, renders its stored HTML to the chosen format
   in memory (no network fetch of embedded resources), and streams it.
4. Response carries the binary, the correct `Content-Type`, and `Content-Disposition:
   attachment` with a filename derived from the document title.
5. Browser downloads the file.

## Acceptance Criteria

- `GET /documents/{id}/export?format=pdf` returns a valid PDF (starts `%PDF`), and
  `format=docx` returns a valid DOCX (a zip, starts `PK`), each with the correct
  `Content-Type`.
- The response sets `Content-Disposition: attachment` with a filename from the document
  title, RFC 5987-encoded for non-ASCII (Cyrillic) and safe against header injection
  (CR/LF or quotes in the title never break out of the header).
- A document absent or owned by another account → 404 (never 403), no file.
- An unsupported or missing `format` → 422, no file.
- An empty document exports to a valid (near-empty) file, not an error.
- A document with no title (a pre-migration row where `title` is null) exports with a
  defined default filename (e.g. `document.pdf`), never an empty or `null` filename.
- The rendered content matches the stored sanitized HTML; export neither runs generation
  nor mutates the document (version unchanged).
- Multibyte content (Cyrillic + emoji + combining accent) renders intact into both PDF and
  DOCX — no mojibake or replacement characters; UTF-8 is pinned at the render encode step.
- A save immediately followed by an export reflects the just-committed content and title,
  read through the primary (no stale replica/cache read).
- Embedded external references in the content (`<img src="http(s)://…">`) never trigger an
  outbound network request during render (SSRF-safe), verified against an observed/fake
  network — they are ignored/blocked.
- A pathological document aborts render within a named wall-clock deadline, the request
  returns the sanctioned error, and the worker/thread is freed (no detached render).
- Repeated exports — including induced render failures — do not grow native/memory
  resources monotonically; concurrent CPU-bound renders are bounded (worker pool /
  backpressure) so simultaneous exports cannot exhaust an instance.
- A render failure/timeout emits an attributable server-side signal (keyed by document id)
  distinct from the happy path.
- Error bodies (404/422/render-failure) expose a stable generic shape — never a DB
  message, filesystem path, id shape, or stack trace.

## Validation Rules

| Field | Rule |
|-------|------|
| document_id | required path param; must be a caller-owned document; else 404 (absent/foreign) |
| format | required query param; one of `pdf`, `docx`; any other value → 422 |
| title (filename) | derived from the document title; RFC 5987-encoded; CR/LF/quotes stripped or encoded — never injected into the response header |

## Screen States

- **Editor with Export control** — a PDF/DOCX choice (menu or two buttons) in the editor.
- **Exporting** — in-flight indicator while the file is being generated.
- **Export error** — inline error (with retry) if the request fails; the document view is
  unchanged.
- **Download delivered** — browser save dialog / file lands in downloads.

Client note: the Export control is disabled while a request is in flight so a double-click
issues a single export. Export renders the *stored* HTML — if the editor holds unsaved
edits, save (or warn) before exporting so the file is not silently stale (seam with the
story-5/18 editor dirty-state guard).

## Core Requirements

- Render on the backend from `Document.content`; DOCX via python-docx/htmldocx, PDF via
  WeasyPrint (or an equivalent that passes the CI `audit` gate).
- The file is generated in memory and streamed; nothing is persisted to disk on any
  instance (multi-instance rule).
- The PDF renderer's network fetch is disabled (WeasyPrint `url_fetcher`) so embedded
  URLs cannot cause SSRF; no external resource is fetched during render.
- Export is a plain synchronous request/response — no queue, no polling, no document
  mutation.
- Owner-scope every export by id; 404 (not 403) for absent/foreign, indistinguishable.
- Filename derivation is header-injection-safe and RFC 5987-encoded for Cyrillic.
- New rendering dependencies (and their system libraries in `backend.Dockerfile`) must be
  installed and pass `pip-audit`. ACTION: WeasyPrint needs libpango/cairo in the image.
- Missing native render libs or an unset render-timeout config fail fast at boot / health
  check, not as a runtime 500 on the first export.
- `title` column on `Document` is shared with the story-5 extension — whichever session
  lands first adds it; export reads it. Old code (unaware of `title`) must still read/serve
  `Document` after the additive column lands (rolling deploy).
