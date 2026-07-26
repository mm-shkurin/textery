# Export document — Notes & Considerations

Companion to `17_ExportDocument.md`. Forced guards from the hazard scan and cross-story
seams. `interview.md` holds decisions; `../../decisions/editable-generated-docs-scope.md`
holds the 3-session scope lock.

## Warnings

### Technical
- WeasyPrint needs system libraries (libpango, cairo, gdk-pixbuf) in the backend image —
  a pure `pip install` is not enough. Missing libs surface as a runtime 500 on first
  export unless a boot/health check catches them.
- The PDF renderer MUST have network fetch disabled (`url_fetcher`) — otherwise an
  `<img src="http://…">` in content is an SSRF vector.
- Render is CPU-heavy; concurrent exports can exhaust an instance without a worker cap.

### UI/UX
- Export renders the *stored* HTML. Unsaved editor edits produce a silently stale file —
  save or warn before exporting.

## Forced guards (fold into test-spec — each must go red on its hazard)

**Encoding / filename (grp 1)**
- Multibyte content (Cyrillic + emoji + combining accent) renders intact into PDF and
  DOCX — no mojibake/replacement char; UTF-8 pinned at the encode step.
- Filename from a Cyrillic/emoji title is RFC 5987-encoded and, if length-capped,
  truncated on a grapheme boundary (or state explicitly there is no cap).

**Boundary / injection (grp 5) — mostly covered**
- IDOR: foreign/absent document → 404, byte-identical, no file.
- Header injection: CR/LF/quotes in the title never break out of `Content-Disposition`.
- `format` fail-closed: unknown/missing → 422, no file.

**Resource / deadline (grp 2, 6)**
- Pathological document aborts render within a named wall-clock deadline; request returns
  the sanctioned error; worker/thread freed, no detached render.
- Repeated exports incl. induced failures → no monotonic native/memory growth.
- Concurrent renders bounded (worker pool / backpressure) — N simultaneous exports cannot
  exhaust an instance.

**Consistency (grp 3)**
- Save-then-export reflects the just-committed content and title (read via primary).

**Schema (grp 4)**
- Pre-migration row (null `title`) → defined default filename, never empty/`null`.
- Old code reads/serves `Document` after the additive `title` column lands (rolling deploy).

**Operability / disclosure (grp 7)**
- Missing native libs / unset render-timeout config → fail fast at boot / health check.
- Render failure/timeout emits an attributable signal keyed by document id; happy path
  does not.
- Error bodies (404/422/render-failure) carry no DB text, filesystem path, id shape, or
  stack; internal detail redacted to a fixed token (assert in body AND logs).

**SSRF (grp 2/5 seam)**
- Content with `<img src>` on a local/external address → renderer makes zero outbound
  request, verified against an observed/fake network.

**Client (grp 8)**
- Export control disabled while in flight → a double-click issues one request.

## Cross-story seams
1. **SSRF / no-external-call** (grp 2 ↔ 5) — one guard: url_fetcher-off test on embedded
   URLs. Owned here (new render path), confirmed carried.
2. **Content-injection sink** — export trusts `Document.content` as already sanitized by
   story-5's `HtmlSanitizer`; confirm that guard exists upstream.
3. **200k content size cap** — enforced at story-5 save; export re-validates nothing. A
   bypassed cap → unbounded in-memory render here. Confirm story-5 carries it.
4. **Render deadline abort** (grp 2 ↔ 6 ↔ 7) — one guard: aborts-at-budget → clean error.
5. **Stale-export-while-dirty** (grp 8 ↔ story 18 editor) — reconcile: export reflects
   unsaved edits, or the UI warns/saves first.
6. **`title` column** — shared additive migration with story-5-extension; first session
   adds it.

## Security Considerations
- SSRF via embedded URLs — url_fetcher off. IDOR — owner-scope, 404 not 403. Header
  injection via filename — RFC 5987 + strip CR/LF/quotes. Disclosure in render errors.

## Integration / Load Notes
- Reuses story-5 `Document`/`GET`. New deps (WeasyPrint, python-docx/htmldocx) + system
  libs; must pass CI `audit`.
- Load profile Throughput: sustained export rate + render-time ceiling (see 03_Load).

## Hazard-scan record
Scanned twice against catalogue **Groups 1–8**:
- Story-level (2026-07-26) — gaps folded into `17_ExportDocument.md` / this Notes.
- Test-level (2026-07-26) — verified each guard is a scenario. Added: filename
  grapheme-truncation cap (or no-cap statement), read-after-write with replica-lag model,
  over-limit-content export boundary, injectable-clock deadline boundary pair.
Groups 5 and 8 clear; 1,2,3,4,6,7 fired gaps, all folded. Re-scan if a Group 9+ is added
while this spec is still open.
