# Manual mode — what the editor actually does today

A feature-level read of Story 5's frontend as it stands on `feature/05-manual-mode-frontend`.
This is the complement to [`progress-frontend.md`](progress-frontend.md): that file tracks
*which work units ran*, this one describes *what a visitor can do* and, just as importantly,
what looks finished but isn't. Where the two disagree, the code wins — everything below was
read from the source, not from the checkboxes.

Scope note, corrected 2026-07-17: the backend is reachable and this story is docked to it.
Everything below marked "measured" was driven against the running stack. What is still only
jsdom-deep is called out where it matters — the distinction is the whole point of this file.

## Docking status: WORKING (2026-07-17)

The editor creates, loads and saves against the live backend, and Story 7's auth is merged, so
manual mode sits behind a session. Verified through the real client with no mocks in the path:

```
CREATE   -> {"documentId":"cb4cdb8b-…","status":"draft","version":1}
SENT     -> <p>Живой текст</p><script>alert(1)</script><br />
SAVE     -> {"version":2,"content":"<p>Живой текст</p><br>"}   <- script stripped, <br /> normalised
GET      -> content:"<p>Живой текст</p><br>"                    <- reopen matches
CONFLICT -> {"version":3,"content":"<p>two</p>"}                <- 409 refetched and retried itself
```

Database, the backend session's own acceptance check (`owner_id` null would mean the token never
arrived):

```
 document_type | status | version |        content         | has_owner
 доклад        | draft  |       3 | <p>two</p>             | t
 доклад        | draft  |       2 | <p>Живой текст</p><br> | t
```

**This section previously listed five blockers. Four are resolved and the fifth was never real** —
recorded rather than quietly deleted, because the reasons matter more than the outcome:

1. ~~No authentication anywhere~~ — Story 7's merge brought `authorizedRequest` (Bearer, one
   renewal per expiry burst, replay). `documentApi` was the last caller of the old auth-free
   client; it now routes through `send` → `authorizedRequest`, so all three calls carry the token.
2. ~~`POST` sends `content: ''` → 422~~ — **the spec was wrong, not the client.** Measured: a POST
   carrying `{"status":"completed","content":"<p>x</p>"}` returns **201** with `status="draft"`,
   `content=""`. Server-owned fields are **ignored, not rejected**. `content` is still not sent,
   but for hygiene — a request should say what it means — not from fear of a 422 that never fires.
3. **`document_type` Latin vs Cyrillic — this was the real blocker, and it settled against us.**
   `docking-requirements.md` asked the backend for Latin; the backend kept Cyrillic. Measured:
   `{"document_type":"doklad"}` → **422 INVALID_DOCUMENT_TYPE**, `{"document_type":"доклад"}` →
   201. `WIRE_DOCUMENT_TYPE` now translates at the API boundary.
4. ~~`version` dropped on create~~ — threaded from the create response and made **required, not
   optional**: an optional field would let `result.version ?? 1` keep the guess alive under a
   green suite, which is exactly what the premortem measured.
5. ~~`Idempotency-Key` minted per call~~ — the caller owns it now (`useDocumentInit` mints one per
   mount into a `useRef`), so StrictMode's double-invoked effect is a replay rather than a second
   document.

**How this stayed invisible:** every `red-frontend-api` step was `[S]`'d as *"no API call:
formatting is client-side editor state only"*. True of toggling marks, false of the payload —
`ManualEditor.tsx` sends `editor.getHTML()` over the wire. 7.9's premortem named that
misclassification and it was recorded, not acted on. The specs were the only contract and nobody
had read them against the client until they were curl'd.

## History — "Мои работы"

A signed-in visitor gets a **Мои работы** action in the header (absent when signed out, because
both list endpoints 401 without a token). It opens a screen with two tabs: **Мои документы** and
**Генерации**, each paging on `GET /api/v1/documents|generations?limit&cursor`.

**Two tabs rather than one merged feed, and the reason is the contract, not taste:** the two
endpoints paginate on independent keyset cursors, so interleaving them by date would either
mis-order rows at page boundaries or require reading both lists to the end before showing
anything. A single feed needs one server-side endpoint.

Clicking a document row reopens it in the manual editor with its saved content — this is what
finally wired `ManualEditor`'s `existingDocumentId`, built back in scenario 6.2 and left
unconnected because until history existed there was no entry point. Back from a history-opened
editor returns to history, not to the mode modal (which would offer to pick a mode for a document
that already has one). **Generation rows are deliberately not clickable**: opening one means the
chat workspace, which this story does not own, and a dead click is worse than an honest absence.

`hasMore` derives from the **cursor**, never `items.length === limit` — the backend's last page
carries items *and* a null cursor. Error beats empty in the row renderer: a failed fetch also
leaves the list empty, and telling someone "you have no documents" when the truth is "we could
not ask" invites them to recreate work that already exists.

## Mobile

The editor and the history screen have real mobile layouts, verified in a 375×812 viewport
(`scrollWidth === clientWidth === 375` on every screen; 0 of 18 toolbar buttons past the right
edge). The toolbar **wraps** rather than scrolling, per the mobile mockup — a horizontal-scroll
toolbar would hide controls behind a gesture nobody is told about. History rows stack so the
document type is not truncated by an ellipsis competing with the date.

Note for anyone re-measuring: `--window-size=375` in headless Chrome yields a **489px** viewport,
because the flag counts browser chrome. Use CDP `Emulation.setDeviceMetricsOverride`. The first
run of this check silently tested the wrong width.

## Getting into the editor

Manual mode is offered alongside AI generation on the mode modal — both cards are live, neither
carries a "скоро" badge. Choosing it fires a `POST` and drops the visitor into an empty editor:
placeholder text, the full formatting toolbar, a breadcrumb carrying the document type, and a
status line reading *Черновик, ещё не сохранён*. There is no intermediate loading skeleton — the
editor is built unconditionally, so it appears at once.

**The editor appears whether or not the `POST` succeeded — still true, and still a real gap.**
The create failure path only `console.error`s (`useDocumentInit.ts`), so a create that fails for
any reason (network, 500, an expired session on a stale tab) leaves the visitor with a
working-looking editor holding no `documentId`. Typing works; saving silently no-ops on
`ManualEditor.tsx`'s `if (!documentId || !editor) return` guard. Nothing tells them. The status
line still reads *Черновик, ещё не сохранён* — true, and misleading about why.

The 422s that used to make this fire on *every* create are fixed, so it is now a rare path rather
than the default one. That makes it less visible, not less real: it is the one failure mode where
the editor lies by looking healthy.

"Назад" returns to the mode modal with the document type still scoped, rather than resetting to
the landing page.

## Writing and formatting

The editor is Tiptap over a deliberately narrow document schema: `Document.extend({ content:
'inline*' })`. The document holds inline content directly, with no paragraph or heading nodes at
all. That single decision shapes everything else. Tiptap's stock block extensions — Blockquote,
CodeBlock, HorizontalRule, Heading — are structurally unreachable under this schema, so each was
re-implemented as a **Mark** rather than a Node: blockquote, code block, H3, and centre-alignment
all wrap a line by applying a mark to it, not by nesting a block. `lineWrapMark.ts` is the shared
factory for the simple single-tag cases; code block (nested `<pre><code>`) and centre-alignment
(a `style` attribute rather than a semantic tag) each needed bespoke handling.

Marks that were already inline fit without ceremony and are plain toggles: bold, italic,
strikethrough, underline, inline code.

Toolbar state follows the cursor, not the document — a button lights up (`aria-pressed`) only
while the caret sits inside text carrying that mark, and goes dark when the caret moves out.
Undo and redo are the only controls with a disabled state rather than an active one; they grey
out when there is nothing to unwind.

**Six of the seventeen toolbar entries are dead.** H1, H2, paragraph, bullet list and ordered
list are the original mockup-era stubs: they still call Tiptap's block-node commands
(`toggleHeading`, `toggleBulletList`, …), which the `inline*` schema makes inert. Italic is a
different case — it works, but has no `testId`, so no test clicks it and nothing renders it
reachable by the same route the others use. None of these six have a scenario of their own; they
are inherited surface, not shipped capability. A toolbar reading "H1 H2 H3 ¶ • 1. B I S U <>"
overstates what the editor can do by a third.

## Saving

Saving is manual — there is no autosave. The save button shows a spinner and disables itself
while a request is in flight, and the status line moves between three states: *Создание
документа…*, *Черновик, ещё не сохранён*, and *Сохранено*.

Concurrency is handled by making it structurally impossible rather than resolving it after the
fact. Only one save is ever in flight; a save requested while one is running sets a flag that the
in-flight save consumes when it settles, firing a fresh save with the then-current content and
the version the server just returned. Saves stay strictly sequential, so there is no
out-of-order response to reconcile and no client-side sequence comparison. The acceptance
scenario asks for a stale response not to win; this design means the race never happens. That is
a stronger guarantee than the Gherkin literally describes — and it also means two genuinely
concurrent requests are never exercised.

A failed save keeps the visitor's content untouched and raises an inline error banner
(`role="alert"`) below the toolbar, cleared on the next successful save.

## Reopening a saved document

`ManualEditor` accepts an optional `existingDocumentId`. When present, it fetches the document,
populates the editor with the stored content, and adopts the returned version so the next save
targets the right base. It works, and it is tested.

**It also has no entry point.** `App.tsx:43` renders `ManualEditor` with `documentType`,
`documentTypeLabel` and `onBack` — never `existingDocumentId`. There is no document list or
history UI in this story (that is story #12), so nothing in the running application can reach
this path. The capability exists at the component boundary and stops there.

## Links (scenario 7.9) — designed, not built

The only frontend scenario still open. The URL-entry interaction was decided in
[`decisions/link-url-input-decision.md`](decisions/link-url-input-decision.md): an inline popover
rather than the `window.prompt` MVP the plan proposed. The reasoning is worth reading before
implementing, because the deciding factor was not UX — it was that `ToolbarAction.run` returns
`void` and discards `setLink`'s rejection, and that jsdom stubs `window.prompt`, so the only
available evidence would be blind to the risk that made `prompt` cheap.

Link ships inside StarterKit already, so it is registered and live today, just not on the
toolbar — including `autolink` and `linkOnPaste`, both of which the ADR turns off.

## What is honestly not verified

Worth stating plainly, because a green suite invites the opposite conclusion:

The **client/server round-trip is untested**. Every `*.parseHTML` test asserts that Tiptap
re-parses markup Tiptap itself just rendered, inside one jsdom process. If the backend sanitises
or re-serialises the HTML — and `target`/`rel` on an anchor is exactly what a sanitiser
targets — every test stays green while the real reload diverges. `editor.getHTML()` is API
surface, so the markup these scenarios produce is a contract nobody has checked against the
other side.

**Nothing protects unsaved work.** `beforeunload`, navigation blockers, `localStorage` — zero
hits across `frontend/src`. Content lives only in Tiptap's in-memory state. The save-error banner
tells the visitor their text is "сохранён локально в редакторе"; that is false, and has been
recorded as an open BLOCK in [`carryover.md`](carryover.md) since scenario 5.2.

**The status line can lie.** `setHasUnsavedChanges(true)` fires from exactly one place —
ProseMirror's DOM `input` handler (`ManualEditor.tsx:118`). Toolbar actions dispatch transactions
programmatically and never emit a DOM `input` event, so applying a format after a successful save
leaves the document changed while the status still reads *Сохранено*. Proven by probe during
7.9's premortem: the content assertion passed and the dirty-label assertion returned null. This
is pre-existing across all seventeen actions rather than anything scenario 7.9 introduced, and it
compounds the banner above: one lie about local persistence, one about remote.

**Coverage numbers are not evidence of round-trips**, and twice now have not been. A mark whose
`parseHTML` returns a bare tag rule is declarative data, so its "100%" is schema-build time, not
parse time. A factory-extracted toggle shares source lines across five marks, so one mark's test
paints all five green. Both patterns are documented with their scars in `carryover.md` and in
7.6/7.7's progress notes.

## Where the state of play lives

- [`progress-frontend.md`](progress-frontend.md) — per-scenario work-unit state, the source of truth for what runs next.
- [`decisions/link-url-input-decision.md`](decisions/link-url-input-decision.md) — the 7.9 URL-input ADR.
- [`carryover.md`](carryover.md) — quirks and scars a future scenario will hit.
- [`tests/02_UI_Tests.md`](tests/02_UI_Tests.md) — the Gherkin these scenarios implement.
- [`plans/jazzy-stirring-key.md`](../../plans/jazzy-stirring-key.md) — the 7.x toolbar plan. Treat its dependency claims with suspicion: it says Underline and Link each need their own package; both ship inside StarterKit, and 7.7 spent a refactor round removing the duplicate registration that claim caused.
