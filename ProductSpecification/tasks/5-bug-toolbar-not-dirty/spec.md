# Task 5: Toolbar actions don't mark the document dirty, so the save status falsely reads "Сохранено"

Type: bug

## Description

In the manual editor (Story 5), applying any formatting via the toolbar after a
successful save leaves the document changed on screen while the save status line
still reads **Сохранено**. The visitor is told their work is persisted when it is
not. Closing the tab at that point loses the change silently — there is no
`beforeunload` guard anywhere in `frontend/src`, so nothing else intervenes.

Affects all 17 entries in `TOOLBAR_ACTIONS`, not one control.

## Reproduction

1. Open the manual editor, type text, click Сохранить, wait for **Сохранено**.
2. Select the text, click any formatting button (e.g. `toolbar-bold`).
3. Observe: the content changes (`<strong>hello</strong> world`), the status line
   still reads **Сохранено**.
   Expected: **Черновик, ещё не сохранён**.

Confirmed by a throwaway probe during scenario 7.9's premortem pass (probe removed,
`git status` clean at the time). Both content assertions passed before the status
assertion failed, which rules out a stored-marks false positive — the document
genuinely diverged from the server:

```
expect(contentArea.innerHTML).toBe('<strong>hello</strong> world')          // PASSED
expect(screen.queryByText('Черновик, ещё не сохранён')).toBeInTheDocument() // FAILED — received null
```

## Root cause (already known — confirmed by probe, not speculative)

`setHasUnsavedChanges(true)` has exactly one call site: the ProseMirror DOM `input`
handler at `frontend/src/features/generation/components/ManualEditor.tsx:117-118`
(`editorProps.handleDOMEvents.input`).

Toolbar actions dispatch ProseMirror transactions programmatically
(`editor.chain().focus().toggleMark(...).run()`). A programmatic transaction changes
the document but emits no DOM `input` event — that event only fires for direct user
input into the contenteditable. So the flag never flips for any toolbar-driven edit.

The trigger is precise: `hasUnsavedChanges` initialises to `true`
(`ManualEditor.tsx:39`), so the bug only manifests **after the first successful
save** resets it to `false` — exactly the state a visitor is in when they go back
over their text to format it.

## Scope

Pre-existing across all 17 toolbar actions since the dirty-flag was introduced in
scenario 5.1. Not introduced by any single scenario. Surfaced during 7.9's design
work unit and deliberately not fixed inline there: that unit was a design/spec step
with no production code, and this defect belongs to none of 7.9's Gherkin.

Related, NOT in this task's scope:
- The save-error banner separately claims content is "сохранён локально в редакторе"
  when no local persistence exists — an open BLOCK recorded in
  `ProductSpecification/stories/05-manual-mode/carryover.md` since scenario 5.2.
  Same family (the UI lying about persistence), different defect.
- The absence of any `beforeunload`/navigation guard. That is what makes this bug
  lose data rather than merely mislead, but adding an exit guard is its own change.

## Fix approach

Tiptap's `useEditor` exposes an `onUpdate` callback that fires on any transaction
that changes the document, regardless of whether it originated from a DOM event or
a programmatic chain. The flag moves from `handleDOMEvents.input` to `onUpdate`.

**Corrected after the hazard scan — this is NOT "one line, covers all 17 actions".**
The original version of this section said exactly that and was wrong on three counts.

**1. The `input` handler does two jobs, not one** (`ManualEditor.tsx:116-129`):

```js
input: (view, event) => {
  setHasUnsavedChanges(true)
  // comment here cites premortem/agent-review CONCERNS on scenario 5.1
  if (isSavingRef.current) {
    saveAgainRequested.current = true   // <-- the second job
  }
  return flushDomObserverOnInput(view, event)
}
```

`saveAgainRequested` is the only thing stopping an in-flight save's resolve handler
from marking the document clean while newer unsent content sits in the editor — put
there by scenario 5.1's premortem. Moving only the flag leaves the queue on the dead
DOM path for toolbar edits: the flag would flip `true`, then the settling save's
`else` branch (`:66-68`) would clobber it back to `false`, and the formatted content
would never be sent. That is **worse than the bug under repair** — a confidently clean
status over content the server has never seen, with no autosave and no `beforeunload`
to catch it. **Both writes move together**, driven by the same user-edit discriminator,
so they cannot drift apart again.

**2. Suppressing the load must be origin-based, not content-based.** Use Tiptap v3's
`setContent`'s `emitUpdate: false` at `useDocumentInit.ts:27` rather than a ref armed
around the call or a before/after content comparison. A ref latch breaks when
`setContent` produces zero transactions (empty or identical content): it stays armed and
swallows the user's next genuine edit. A content comparison breaks on Cyrillic —
`setContent`'s parse-and-re-serialize can renormalize text so an untouched loaded
document compares unequal and pins to `Черновик` forever, which every ASCII fixture in
this suite would miss.

**3. Suppression alone leaves the load in the wrong state.** `hasUnsavedChanges`
initialises to `true` (`:39`), so merely *not marking* a loaded document dirty still
renders **Черновик, ещё не сохранён** for a freshly-reopened, untouched saved document.
The load path must *actively* set clean. This already misreports today, in the opposite
direction from the headline bug.

**Fail-safe direction:** unknown origin → dirty. A spurious `Черновик` is cosmetic; a
spurious `Сохранено` is this bug. The `setContent` suppression is the narrow exception,
never the fallthrough.

## Hazard scan (steps discovery gate)

All 8 groups in `.claude/guidelines/hazard-catalogue/_index.md` dispatched, one pass
each, none skipped. Group 06 returned CLEAR — and disproved the amplification worry it
was pointed at: the per-keystroke `setState` already exists on the DOM path,
`shouldRerenderOnTransaction: true` is already on (`:89`), and a same-value `setState`
bails, so the fix's per-transaction work is ≤ today's. Groups 01/02/03/04/05/07/08 fired.

Folded into red steps below: the in-flight toolbar twin (02, 03, 04, 05, 07, 08 all
converged on one guard), the load direction with its init-`true` masking trap (04, 08),
the first-edit-after-load fail-open (05), and the failed-save flag pin (07).

Dismissed with reason:
- **Exit guard (`beforeunload`/`useBlocker`) — 08's GAP 4.** Real, and the reason this
  bug loses data rather than merely misleads. Separate change; belongs with the open
  BLOCK in `carryover.md` (the banner claiming local persistence). `onBack` (`:142`)
  unmounting with no dirty check is the same hazard. Noted there, not fixed here.
- **Idempotency of the queued re-save — 08's GAP 3.** A server property; backend is on a
  parallel branch and unreachable, so no guard can be written here.
- **`console.error` carries no documentId — 07's GAP 3.** Pre-existing; the fix touches
  neither the catch nor the error contract.
- **Double-click-Save exactly-once — 08's GAP 2.** Pre-existing and adjacent; scenario
  4.2 already covers the queue via the input path.
- **Multibyte round-trip fixture — 01.** Moot once the discriminator is origin-based: no
  code path compares content, so renormalization cannot mislead it.

## Acceptance scope

The fix changes externally observable behavior (the status line), which normally forces a
`red-acceptance`/`green-acceptance` pair. Not available here: the backend is on a parallel
branch and every Selenium step in the related story is `[S]` under that story's standing
policy. Recorded rather than silently skipped — an acceptance-level guard for this fix is
owed once a live backend reaches this branch.
