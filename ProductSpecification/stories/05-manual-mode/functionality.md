# Manual mode — what the editor actually does today

A feature-level read of Story 5's frontend as it stands on `feature/05-manual-mode-frontend`.
This is the complement to [`progress-frontend.md`](progress-frontend.md): that file tracks
*which work units ran*, this one describes *what a visitor can do* and, just as importantly,
what looks finished but isn't. Where the two disagree, the code wins — everything below was
read from the source, not from the checkboxes.

Scope note: the backend is developed on a parallel branch and is unreachable here. Every
Selenium and demo step in this story is `[S]`, so **nothing below has ever run in a real
browser against a real server**. The evidence is 76 jsdom component tests.

## Getting into the editor

Manual mode is offered alongside AI generation on the mode modal — both cards are live, neither
carries a "скоро" badge. Choosing it creates a document immediately (`POST`) and drops the
visitor into an empty editor: placeholder text, the full formatting toolbar, a breadcrumb
carrying the document type, and a status line reading *Черновик, ещё не сохранён*. There is no
intermediate loading skeleton — the editor is built unconditionally, so it appears at once.

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

**The five inert toolbar stubs were removed (2026-07-23).** H1, H2, paragraph, bullet list and
ordered list were mockup-era stubs calling Tiptap's block-node commands (`toggleHeading`,
`toggleBulletList`, …), which the `inline*` schema makes inert — they rendered but did nothing.
They had no scenario of their own; showing them overstated the editor by a third. Removed from
`TOOLBAR_ACTIONS` (and `ToolbarActionKey`) so the toolbar reflects real capability; scenario
2.1's Gherkin and acceptance check were updated to the working named controls (H3, bold, italic).
Restoring real headings/lists requires migrating the schema to block content — a separate story.
Remaining note: italic works but still has no `testId`, so it is reachable by `aria-label`
(`Курсив`) but not by the `toolbar-*` route its siblings use.

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
