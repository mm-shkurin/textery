# Editor pages — Notes & Considerations

## Warnings

### Functional Warnings

- **The default preset is the worst possible test fixture.** A4 portrait / 20-10-20-30 /
  14 pt / 1.5 is the combination most likely to be hardcoded independently in the editor CSS,
  the PDF stylesheet and the DOCX section defaults. A geometry test on the preset passes with
  every unit conversion broken. Hence the spec's insistence on a self-distinct fixture where
  no two numbers are equal.
- **Whole-object replace is a data-loss shape if the client is naive.** A panel that sends
  only the field the user touched wipes the header, footer and numbering flags back to
  defaults, and every acceptance criterion still passes. The page-setup panel must hold and
  send the complete object.
- **A "non-zero content box" is not the same as a usable one.** 72 pt text at line height 3.0
  on A5 landscape with large margins leaves a box that is positive but shorter than one line.
  Naive pagination then emits an unbounded stream of empty pages — the browser hangs, and the
  synchronous export pins a request thread until its deadline. This is why the validation rule
  is "fits at least one line", not "> 0".
- **Manual breaks and re-flow interact.** A break stored as content survives an edit above it;
  a break tracked by page index does not. The second is easier to build and silently wrong the
  first time a user types a paragraph on page 1.
- **`volume_pages` divergence is informational.** Showing "3 из запрошенных 5" invites the
  user to expect a fix button. There is none in this story — the wording should not imply one.

### UI/UX Warnings

- **The font-loading window is visible.** Layout cannot start before the face resolves, so a
  document briefly has no page count. Left unspecified, that renders as a perpetual spinner or
  a flash of unpaginated content that then reflows. It needs its own designed state.
- **Rejected geometry must roll the view back.** If the editor repaginates optimistically and
  the server rejects, an inline field error alone leaves the browser laid out against geometry
  the server does not hold — and the export then silently disagrees with the screen.
- **Two save paths, one endpoint.** Story 5's debounced content autosave and the page-setup
  save both `PUT /documents/{id}`. Out-of-order responses are the ordinary case, not the edge.
- **Header/footer text is free typed text and the most losable thing in the panel.** The
  existing `beforeunload` guard watches content only.

### Technical Warnings

- **Three unit systems, three boundaries.** mm (WeasyPrint), CSS px at 96/inch (browser), EMU
  at 914400/inch and half-points and twips (python-docx). Nothing but a test on distinct values
  catches a dropped factor; field names are not evidence of units.
- **JSONB accepts what the validator forgot.** Persisting the request sub-object verbatim means
  every key the value object does not enumerate lands in storage and returns on read. Re-serialize
  from the validated object.
- **Locale is an unpinned ambient in the render container.** Under a comma-decimal locale,
  `line-height: 1,5` is an invalid CSS declaration that drops silently — the page count changes
  and nothing errors.
- **WeasyPrint's blocked fetcher does not fail the render.** `_blocked_url_fetcher` raises per
  resource; WeasyPrint logs and continues. A missing or unfetchable font therefore yields a
  successful 200 PDF in substituted metrics. Font resolution must be checked explicitly, not
  inferred from the render succeeding.
- **`Document.version` and `save_content_if_version_matches` already exist** — story 5 built the
  CAS. Settings must ride it rather than adding a second concurrency mechanism.
- **The N-1 *write* path is the untested half of the rolling deploy.** Old code reading the row
  is the obvious case and is already in story 17's posture; old code *saving* the row with a
  full-column UPDATE nulls `page_settings` for anyone whose request lands on an old instance.

---

## Suggestions & Future Enhancements

### Functional Suggestions

- A "fit to N pages" action that nudges line height or margins to hit the requested
  `volume_pages` — the obvious next step once divergence is visible.
- Widow/orphan control and "keep with next" for headings; ordinary in Word, absent here.
- A page thumbnail rail for navigating long documents.
- Section-scoped page setup (different geometry for the title page) — deliberately out of scope;
  it changes `page_settings` from one object to a list and should not be retrofitted casually.

### UI/UX Suggestions

- Ruler with draggable margin handles instead of four numeric inputs.
- Zoom / fit-width, which becomes meaningful the moment content is on sheets.
- Show the manual break as a labelled divider ("Разрыв страницы") rather than a bare line, so
  it is obviously deletable.

### Technical Suggestions

- Measure with `IntersectionObserver` / `ResizeObserver` over a `requestIdleCallback` queue
  rather than a synchronous pass, so a long document degrades in latency and not in
  responsiveness.
- Consider CSS `break-before`/`break-after` and `@page` for the editor as well, so the editor's
  own print path agrees with its screen layout for free.
- The measurement cache keyed by (block id, geometry hash) invalidates correctly on a settings
  change without a separate flush path.

---

## Technical Notes

### Load Considerations

Per `ExpectedLoad.md` the system targets hundreds of concurrent users. Pagination itself is
client-side and costs the server nothing. The server-side risk is export: story 10 makes each
render strictly more expensive (full geometry, headers/footers, numbering), and export is
synchronous, so each in-flight render holds a request thread. Story 17 already requires
bounded concurrent renders and a render deadline — story 10 must not regress either, and the
new geometry must not push a max-size document past the existing deadline.

The client-side budgets (≤ 2 s initial layout, ≤ 150 ms incremental) are first-pass numbers
chosen to be assertable; confirm them against a real max-size document during `/test-spec`
rather than treating them as measured.

### Security Considerations

- **Injection into three sinks.** `header_text` reaches editor HTML, PDF, and DOCX header XML.
  DOCX header XML is the least familiar of the three and the easiest to get wrong — raw text
  written into an XML part, not through an escaping API, is a well-formedness break at best.
- **CSS injection via geometry.** A geometry value string-interpolated into `@page` breaks out
  of the declaration if it passes a loose numeric parse. Typed numbers from the value object,
  never request strings.
- **IDOR on the export path.** Export now carries the owner's header/footer text — a document
  that leaks through export leaks more than before. The 404-not-403 rule extends to it.
- **Error-body disclosure.** A JSONB column plus a domain value object is the classic shape
  that leaks a deserializer message or a JSON path into a 422.
- **DOCX metadata redaction** was written against the pre-headers renderer and must be
  re-asserted after the extension.

### Infrastructure Notes

The bundled font is a new build-time asset that must be present in both the frontend bundle and
whatever the backend renderer reads. Its absence currently degrades silently (see Technical
Warnings), so a startup check is the guard — consistent with story 17's existing rule that
missing native render libs fail fast at boot rather than as a runtime 500.

No new service, no new container, no compose change: the PDF engine stays WeasyPrint in this
story (known-debt #14).

### Integration Notes

- Story 17 (export) — extended, not replaced. Its scenarios stay valid; the regression criterion
  ("default settings, no manual breaks → unchanged output") is what protects them.
- Story 5 (manual mode) — shares the editor and the `HtmlSanitizer` allowlist. The page-break
  allowlist entry collides with story 5's paste-sanitize scenario E5.1; whichever lands first
  owns the change.
- Stories 1 / 18 — supply `volume_pages`, read-only here.

---

## Additional Context

See `interview.md` for the WYSIWYG discussion and why the PDF-engine swap was deferred, the font
licensing constraint, and the build-order rationale. The two deferrals are recorded as
known-debt #14 (editor↔PDF page equality unmeasured) and #15 (single bundled font, no font
choice) in `.memory-bank/tasks/known-debt.md`.

## Hazard-scan record

Scanned 2026-08-01 against groups **1–8** (the `_index.md` **Groups** list at scan time). A
group added later obligates a re-scan while this spec is still being worked.

| Group | Verdict |
|-------|---------|
| 1 Money, numbers & representation | 3 fired, 3 gaps — all folded (units per boundary + self-distinct fixture, inclusive bounds + edge fixtures + fit-rule at exact equality, NFC + length unit + invariant locale) |
| 2 Re-run safety, ordering & atomicity | 4 fired, 4 gaps — folded (PUT replay idempotence, whole-request rejection leaves content byte-identical, font-load timeout + defined outcome, named budgets + abort). Compute-then-commit dismissed: no per-iteration side effect |
| 3 Concurrency, consistency & distribution | 4 fired, 4 gaps — folded onto the existing version CAS (atomic merge, stale-version rejection, export reads post-save state). Async-delivery/poison narrowed: export is synchronous, so the guard is the deadline + thread release, not a dead-letter state |
| 4 Data lifecycle & schema | 2 fired, 4 gaps — folded (N-1 *write* path preserves the column, read policy for undefined stored key/enum, replace-vs-merge stated explicitly, reset is deliberate). State-machine class dismissed: story adds no lifecycle |
| 5 Request boundary & input | 5 fired, 4 gaps — folded (export in the owner-scope criterion, re-serialize from the value object, typed numbers into the CSS sink, read policy for unmapped stored enum). Absent-vs-null was already covered |
| 6 Scale & resource limits | 3 fired, 4 gaps — folded (header/footer length number, block-count + nesting-depth bounds, geometry must fit one line, bounded measurement cache). Export concurrency deferred to story 17's existing bound with a no-regression criterion. Retry-storm and cursor-stability classes dismissed: no retry path, no list endpoint |
| 7 Time, operability & disclosure | 4 fired, 6 gaps — folded (named budgets, font failure is hard not silent, incremental-vs-full equivalence, no partial export success, startup font validation, sanitized error bodies + DOCX redaction re-assert). Clock/expiry half dismissed: nothing time-derived |
| 8 Client / frontend | 2 fired, 4 gaps — folded (response ordering, optimistic rollback, in-flight control lock, dirty-state covers panel edits, loading/error/empty states named) |

**Seam synthesis.** Six seams were flagged across passes; each is closed by exactly one named
guard rather than by mutual assumption:

1. *Deadline / bounded work* (2 × 6 × 7) → the budgets in Validation Rules plus the abort-and-free
   criterion. Groups 6 and 7 do not restate it.
2. *Concurrent saves* (3 × 4 × 5 × 8) → **two** guards, deliberately: the server-side CAS
   criterion (group 3) and the client-side response-ordering criterion (group 8). Neither
   implies the other — a server that merges correctly still renders stale geometry.
3. *Header/footer text* (1 × 5 × 7) → one criterion covering NFC + length unit, one covering
   escaping at every sink including the editor and logs, one covering disclosure in error bodies.
4. *Font* (2 × 7 × 8) → startup validation (7), hard-failure-not-substitution (7), load timeout
   with a defined outcome (2), and the measuring state (8).
5. *Export double-activation* (2 × 6 × 8) → the client in-flight lock; export being synchronous
   and idempotent (no artifact persisted) makes a server-side dedupe unnecessary.
6. *Unknown stored key / enum* (4 × 5) → the single read-policy criterion (preserve, read as
   default, never crash or downgrade the object).

**Dismissed, not skipped:** compute-then-commit (group 2), state-machine correctness (group 4),
retry storms and cursor stability (group 6), clock/timezone/expiry (group 7) — each for the
reason stated in its row above.
